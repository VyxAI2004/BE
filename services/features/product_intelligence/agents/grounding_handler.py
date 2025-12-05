from typing import Optional
from schemas.product_ai import GroundingMetadata


class GroundingHandler:

    @staticmethod
    def create_search_tools(provider: str) -> Optional[list]:

        if provider.lower() in ["google", "gemini"]:

            from google.genai import types
            return [types.Tool(google_search=types.GoogleSearch())]

        return None
    
    @staticmethod
    def extract_grounding_metadata(llm_response) -> Optional[GroundingMetadata]:
        """Extract grounding metadata and return as Pydantic model"""
        raw_response = llm_response.raw
        
        if hasattr(raw_response, 'candidates') and raw_response.candidates:
            candidate = raw_response.candidates[0]
            if hasattr(candidate, 'grounding_metadata'):
                metadata = candidate.grounding_metadata
                
                # Safe grounding_supports count
                grounding_supports_count = 0
                if hasattr(metadata, 'grounding_supports') and metadata.grounding_supports is not None:
                    grounding_supports_count = len(metadata.grounding_supports)
                
                return GroundingMetadata(
                    grounding_supports=grounding_supports_count,
                    search_entry_point="Google Search was used" if hasattr(metadata, 'search_entry_point') else None
                )
        
        return None
