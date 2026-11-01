from pathlib import Path
import torch
from PIL import Image
from transformers import (
    AutoImageProcessor,
    AutoModelForImageClassification
)

MODEL_NAME = "prithivMLmods/Deep-Fake-Detector-v2-Model"

_processor = None
_model = None


def load_face_detector():
    global _processor, _model

    if _model is None:
        _processor = AutoImageProcessor.from_pretrained(
            MODEL_NAME
        )

        _model = AutoModelForImageClassification.from_pretrained(
            MODEL_NAME
        )

        _model.to(torch.device("cpu"))
        _model.eval()

    return _processor, _model


def analyze_face(image_path):
    try:
        path = Path(image_path)

        if not path.exists():
            return {
                "status": "error",
                "message": "Image file not found."
            }

        with Image.open(path) as image:
            image = image.convert("RGB")

        processor, model = load_face_detector()

        inputs = processor(
            images=image,
            return_tensors="pt"
        )

        with torch.inference_mode():
            outputs = model(**inputs)
            probabilities = torch.softmax(
                outputs.logits,
                dim=-1
            )[0]

        predictions = []

        for index, score in enumerate(probabilities):
            label = model.config.id2label.get(
                index, str(index)
            )

            predictions.append({
                "label": label,
                "score": round(float(score), 4)
            })

        predictions.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        top = predictions[0]

        return {
            "status": "success",
            "prediction": top["label"],
            "confidence": round(
                top["score"] * 100, 2
            ),
            "predictions": predictions,
            "model": MODEL_NAME,
            "analysis_note": (
                "This is an image classifier. It does not "
                "locate or crop faces and is not proof."
            )
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }