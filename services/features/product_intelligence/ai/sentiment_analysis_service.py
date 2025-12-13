import logging
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
SENTIMENT_MODEL_PATH = MODEL_DIR / "sentiment_review.onnx"


class SentimentAnalysisService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        try:
            if not SENTIMENT_MODEL_PATH.exists():
                raise FileNotFoundError(str(SENTIMENT_MODEL_PATH))

            self.model = ort.InferenceSession(
                str(SENTIMENT_MODEL_PATH),
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
                "sentiment_label": "neutral",
                "sentiment_score": 0.5,
                "sentiment_confidence": 0.5,
                "probabilities": {
                    "positive": 0.33,
                    "neutral": 0.34,
                    "negative": 0.33,
                },
                "model_version": "fallback",
            }

        if not text or not text.strip():
            return {
                "sentiment_label": "neutral",
                "sentiment_score": 0.5,
                "sentiment_confidence": 1.0,
                "probabilities": {
                    "positive": 0.0,
                    "neutral": 1.0,
                    "negative": 0.0,
                },
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

            if len(probabilities) == 3:
                probs = {
                    "negative": float(probabilities[0]),
                    "neutral": float(probabilities[1]),
                    "positive": float(probabilities[2]),
                }
            elif len(probabilities) == 2:
                probs = {
                    "negative": float(probabilities[0]),
                    "neutral": 0.0,
                    "positive": float(probabilities[1]),
                }
            else:
                probs = {
                    "negative": 0.0,
                    "neutral": 0.0,
                    "positive": float(probabilities[0]),
                }

            for k in probs:
                probs[k] = max(0.0, min(1.0, probs[k]))

            sentiment_label = max(probs, key=probs.get)
            total = sum(probs.values())
            sentiment_score = (
                (probs["positive"] + 0.5 * probs["neutral"]) / total
                if total > 0
                else 0.5
            )
            confidence = probs[sentiment_label]

            return {
                "sentiment_label": sentiment_label,
                "sentiment_score": round(sentiment_score, 4),
                "sentiment_confidence": round(confidence, 4),
                "probabilities": {
                    k: round(v, 4) for k, v in probs.items()
                },
                "model_version": "1.0",
            }

        except Exception:
            return {
                "sentiment_label": "neutral",
                "sentiment_score": 0.5,
                "sentiment_confidence": 0.5,
                "probabilities": {
                    "positive": 0.33,
                    "neutral": 0.34,
                    "negative": 0.33,
                },
                "model_version": "error",
            }

    def batch_predict(self, texts: list[str]) -> list[dict]:
        return [self.predict(text) for text in texts]


_sentiment_analysis_service: Optional[SentimentAnalysisService] = None


def get_sentiment_analysis_service() -> SentimentAnalysisService:
    global _sentiment_analysis_service
    if _sentiment_analysis_service is None:
        _sentiment_analysis_service = SentimentAnalysisService()
    return _sentiment_analysis_service
