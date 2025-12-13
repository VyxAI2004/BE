import logging
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
SPAM_MODEL_PATH = MODEL_DIR / "spam_review.onnx"


class SpamDetectionService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        try:
            if not SPAM_MODEL_PATH.exists():
                raise FileNotFoundError(str(SPAM_MODEL_PATH))

            self.model = ort.InferenceSession(
                str(SPAM_MODEL_PATH),
                providers=["CPUExecutionProvider"],
            )

            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    "vinai/phobert-base"
                )
            except Exception:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    "bert-base-multilingual-cased"
                )

        except Exception:
            self.model = None
            self.tokenizer = None

    def predict(self, text: str) -> dict:
        if not self.model or not self.tokenizer:
            return {
                "is_spam": False,
                "spam_score": 0.5,
                "spam_confidence": 0.5,
                "model_version": "fallback",
            }

        if not text or not text.strip():
            return {
                "is_spam": False,
                "spam_score": 0.0,
                "spam_confidence": 1.0,
                "model_version": "1.0",
            }

        try:
            encoded = self.tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="np",
            )

            input_dict = {}
            for inp in self.model.get_inputs():
                name = inp.name.lower()
                if "input_ids" in name:
                    input_dict[inp.name] = encoded["input_ids"].astype(
                        np.int64
                    )
                elif "attention_mask" in name:
                    input_dict[inp.name] = encoded[
                        "attention_mask"
                    ].astype(np.int64)

            outputs = self.model.run(None, input_dict)
            logits = outputs[0][0] if outputs[0].ndim == 2 else outputs[0]

            exp_logits = np.exp(logits - np.max(logits))
            probabilities = exp_logits / np.sum(exp_logits)

            if len(probabilities) == 2:
                spam_score = float(probabilities[1])
            else:
                spam_score = float(probabilities[0])

            spam_score = max(0.0, min(1.0, spam_score))
            is_spam = spam_score > 0.5
            confidence = abs(spam_score - 0.5) * 2

            return {
                "is_spam": bool(is_spam),
                "spam_score": round(spam_score, 4),
                "spam_confidence": round(confidence, 4),
                "model_version": "1.0",
            }

        except Exception:
            return {
                "is_spam": False,
                "spam_score": 0.5,
                "spam_confidence": 0.5,
                "model_version": "error",
            }

    def batch_predict(self, texts: list[str]) -> list[dict]:
        return [self.predict(text) for text in texts]


_spam_detection_service: Optional[SpamDetectionService] = None


def get_spam_detection_service() -> SpamDetectionService:
    global _spam_detection_service
    if _spam_detection_service is None:
        _spam_detection_service = SpamDetectionService()
    return _spam_detection_service
