"""
Service để detect spam reviews sử dụng ONNX model.
"""
import os
from pathlib import Path
from typing import Optional
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

# Model path
MODEL_DIR = Path(__file__).parent.parent.parent / "ai_models"
SPAM_MODEL_PATH = MODEL_DIR / "spam_review.onnx"


class SpamDetectionService:
    """Service để detect spam reviews sử dụng ONNX model"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load ONNX model và tokenizer"""
        try:
            if not SPAM_MODEL_PATH.exists():
                raise FileNotFoundError(f"Model file not found: {SPAM_MODEL_PATH}")
            
            # Load ONNX model
            self.model = ort.InferenceSession(
                str(SPAM_MODEL_PATH),
                providers=['CPUExecutionProvider']
            )
            
            # Load tokenizer (assuming using a Vietnamese BERT model)
            # You may need to adjust the model name based on your tokenizer
            try:
                self.tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base")
            except Exception:
                # Fallback to a simpler tokenizer if phobert is not available
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained("bert-base-multilingual-cased")
                except Exception as e:
                    print(f"Warning: Could not load tokenizer: {e}")
                    self.tokenizer = None
            
        except Exception as e:
            print(f"Error loading spam detection model: {e}")
            self.model = None
            self.tokenizer = None
    
    def predict(self, text: str) -> dict:
        """
        Predict spam cho một review text.
        
        Args:
            text: Review content
            
        Returns:
            {
                "is_spam": bool,
                "spam_score": float (0-1),
                "spam_confidence": float (0-1),
                "model_version": str
            }
        """
        if not self.model or not self.tokenizer:
            # Fallback: return neutral prediction
            return {
                "is_spam": False,
                "spam_score": 0.5,
                "spam_confidence": 0.5,
                "model_version": "fallback",
                "error": "Model not loaded"
            }
        
        try:
            # Tokenize input
            if not text or not text.strip():
                return {
                    "is_spam": False,
                    "spam_score": 0.0,
                    "spam_confidence": 1.0,
                    "model_version": "1.0"
                }
            
            # Tokenize
            encoded = self.tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="np"
            )
            
            # Get input names from model
            input_name = self.model.get_inputs()[0].name
            
            # Run inference
            outputs = self.model.run(
                None,
                {input_name: encoded['input_ids'].astype(np.int64)}
            )
            
            # Extract prediction
            # Assuming output is [batch_size, num_classes] or [batch_size]
            if len(outputs[0].shape) == 2:
                # Multi-class output, get probabilities
                probabilities = outputs[0][0]
                spam_score = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])
            else:
                # Single output
                spam_score = float(outputs[0][0])
            
            # Determine if spam (threshold = 0.5)
            is_spam = spam_score > 0.5
            
            # Calculate confidence (distance from threshold)
            confidence = abs(spam_score - 0.5) * 2  # Scale to 0-1
            
            return {
                "is_spam": bool(is_spam),
                "spam_score": round(float(spam_score), 4),
                "spam_confidence": round(float(confidence), 4),
                "model_version": "1.0"
            }
            
        except Exception as e:
            print(f"Error predicting spam: {e}")
            # Return neutral prediction on error
            return {
                "is_spam": False,
                "spam_score": 0.5,
                "spam_confidence": 0.5,
                "model_version": "error",
                "error": str(e)
            }
    
    def batch_predict(self, texts: list[str]) -> list[dict]:
        """Predict spam cho nhiều reviews cùng lúc"""
        return [self.predict(text) for text in texts]


# Singleton instance
_spam_detection_service: Optional[SpamDetectionService] = None


def get_spam_detection_service() -> SpamDetectionService:
    """Get singleton instance of SpamDetectionService"""
    global _spam_detection_service
    if _spam_detection_service is None:
        _spam_detection_service = SpamDetectionService()
    return _spam_detection_service

