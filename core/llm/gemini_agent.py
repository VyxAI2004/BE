import logging
import os
import time
from typing import Any, Optional

from google import genai
from google.genai import types

# Try to import google.api_core exceptions for better error handling
try:
    from google.api_core import exceptions as google_exceptions
except ImportError:
    google_exceptions = None

# Import settings để lấy GEMINI_BASE_URL
from core.settings import settings

from .base import BaseAgent
from .types import LLMResponse

logger = logging.getLogger(__name__)

class GeminiAgent(BaseAgent):
    def __init__(self, model: str = "gemini-2.5-flash", api_key: Optional[str] = None, **kwargs):
        self._model = model
        self.config = kwargs
        # Retry configuration
        self.max_retries = kwargs.get("max_retries", 3)
        self.retry_delay = kwargs.get("retry_delay", 2.0)  # Initial delay in seconds
        
        # Get base_url from kwargs (can be passed from ai_model.base_url) or from settings
        base_url_from_kwargs = kwargs.get("base_url")
        base_url = base_url_from_kwargs or settings.GEMINI_BASE_URL
        
        # Cấu hình http_options nếu có custom base url
        http_options = {}
        if base_url:
            # Ensure base_url doesn't have trailing slash (Google SDK may add it)
            base_url = base_url.rstrip('/')
            http_options["base_url"] = base_url
            logger.info(f"GeminiAgent: Using custom base_url: {base_url}")
            # Nếu server nội bộ yêu cầu version cụ thể, bạn có thể cần thêm:
            # http_options["api_version"] = "v1beta"
        else:
            logger.info("GeminiAgent: Using default Google API endpoint (https://generativelanguage.googleapis.com/)")
        
        # Convert dict to HttpOptions if needed
        if http_options:
            http_options_obj = types.HttpOptions(**http_options)
        else:
            http_options_obj = None
        
        # Truyền http_options vào Client
        try:
            if api_key:
                if http_options_obj:
                    self.client = genai.Client(api_key=api_key, http_options=http_options_obj)
                else:
                    self.client = genai.Client(api_key=api_key)
            else:
                if http_options_obj:
                    # For custom endpoints without API key, SDK may still require api_key parameter
                    # Try without api_key first, fallback to dummy key if needed
                    try:
                        self.client = genai.Client(http_options=http_options_obj)
                        logger.info("GeminiAgent: Client initialized without API key for custom endpoint")
                    except Exception as e:
                        logger.warning(f"GeminiAgent: Failed to initialize without API key: {str(e)}, trying with dummy key")
                        # Fallback: use dummy key for custom endpoints
                        dummy_key = "dummy-key-for-custom-endpoint"
                        self.client = genai.Client(api_key=dummy_key, http_options=http_options_obj)
                else:
                    self.client = genai.Client()
                    if not api_key:
                        logger.warning("GeminiAgent: No API key provided for default Google endpoint - this may cause errors")
        except Exception as e:
            logger.error(f"GeminiAgent: Failed to initialize client: {str(e)}")
            raise

    def model_name(self) -> str:
        return self._model

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable (503, 429, or other transient errors)"""
        error_str = str(error).lower()
        error_repr = repr(error).lower()
        
        # Check for 503 errors
        if "503" in error_str or "503" in error_repr:
            return True
        if "unavailable" in error_str or "unavailable" in error_repr:
            return True
        if "overloaded" in error_str or "overloaded" in error_repr:
            return True
        
        # Check for 429 (rate limit)
        if "429" in error_str or "429" in error_repr:
            return True
        if "rate limit" in error_str or "rate limit" in error_repr:
            return True
        
        # Check for Google API exceptions (if available)
        if google_exceptions:
            if isinstance(error, google_exceptions.ServiceUnavailable):
                return True
            if isinstance(error, google_exceptions.TooManyRequests):
                return True
            if isinstance(error, google_exceptions.ResourceExhausted):
                return True
        
        # Check error attributes
        if hasattr(error, "status_code"):
            if error.status_code in [503, 429, 500, 502, 504]:
                return True
        
        if hasattr(error, "code"):
            if error.code in [503, 429, 500, 502, 504]:
                return True
        
        return False

    def generate(
        self, 
        prompt: str, 
        tools: Optional[list] = None, 
        response_schema: Optional[Any] = None, 
        json_mode: bool = False,
        timeout: Optional[float] = 30.0
    ) -> LLMResponse:
        config = types.GenerateContentConfig(
            tools=tools,
            response_mime_type="application/json" if json_mode or response_schema else None,
            response_schema=response_schema,
        )

        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = self.client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=config
                )

                text = getattr(resp, "text", "") or ""
                meta = {}
                if hasattr(resp, "usage_metadata"):
                    meta["usage"] = {
                        "prompt_token_count": resp.usage_metadata.prompt_token_count,
                        "candidates_token_count": resp.usage_metadata.candidates_token_count,
                        "total_token_count": resp.usage_metadata.total_token_count
                    }

                return LLMResponse(
                    text=text,
                    raw=resp,
                    provider="google",
                    model=self._model,
                    meta=meta
                )

            except Exception as e:
                last_error = e
                is_retryable = self._is_retryable_error(e)
                
                if is_retryable and attempt < self.max_retries - 1:
                    # Exponential backoff: delay = initial_delay * (2 ^ attempt)
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Gemini API error (attempt {attempt + 1}/{self.max_retries}): {str(e)}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Not retryable or last attempt
                    if is_retryable:
                        logger.error(
                            f"Gemini API error after {self.max_retries} attempts: {str(e)}"
                        )
                    else:
                        logger.error(f"Gemini API error (non-retryable): {str(e)}")
                    raise
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise Exception("Unknown error in Gemini agent")
