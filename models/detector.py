from pathlib import Path
import sys
import torch
from PIL import Image
from huggingface_hub import snapshot_download

MODEL_NAME = "abacusai/Smaug-AI-Image-Detector"
AI_THRESHOLD = 0.50

_detector = None


def load_detector():
    global _detector

    if _detector is None:
        torch.set_num_threads(4)

        model_path = snapshot_download(
            repo_id=MODEL_NAME
        )

        if model_path not in sys.path:
            sys.path.insert(0, model_path)

        from smaug_image_detect import SmaugImageDetect

        _detector = SmaugImageDetect.from_pretrained(
            model_path
        )

    return _detector


def analyze_image(image_path):
    try:
        path = Path(image_path)

        if not path.exists():
            return {
                "status": "error",
                "message": "Image file not found."
            }

        with Image.open(path) as image:
            image.verify()

        ai_probability = float(
            load_detector()(str(path))
        )

        if not 0 <= ai_probability <= 1:
            raise ValueError("Invalid model probability.")

        real_probability = 1.0 - ai_probability

        verdict = (
            "ai-generated"
            if ai_probability >= AI_THRESHOLD
            else "real"
        )

        return {
            "status": "success",
            "verdict": verdict,
            "confidence": round(
                max(ai_probability, real_probability) * 100,
                2
            ),
            "ai_probability": round(
                ai_probability * 100, 2
            ),
            "real_probability": round(
                real_probability * 100, 2
            ),
            "model": MODEL_NAME,
            "analysis_note": (
                "Whole-image probabilistic assessment, "
                "not proof of authenticity."
            )
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }