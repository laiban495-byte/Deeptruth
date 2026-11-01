from pathlib import Path
import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

MODEL_NAME = "Salesforce/blip-image-captioning-base"

_processor = None
_model = None


def load_model():
    global _processor, _model

    if _processor is None or _model is None:
        torch.set_num_threads(4)
        _processor = BlipProcessor.from_pretrained(MODEL_NAME)
        _model = BlipForConditionalGeneration.from_pretrained(MODEL_NAME)
        _model.eval()

    return _processor, _model


def generate_image_prompt(image_path):
    path = Path(image_path)

    if not path.is_file():
        return {"status": "error", "message": "Image file not found."}

    try:
        processor, model = load_model()

        with Image.open(path) as source:
            image = source.convert("RGB")

        inputs = processor(images=image, return_tensors="pt")

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=70,
                num_beams=4
            )

        caption = processor.decode(
            output[0],
            skip_special_tokens=True
        ).strip()

        if not caption:
            raise ValueError("No image description was generated.")

        prompt = (
            f"Create an image showing {caption}. "
            "Preserve the main subject, composition, background, "
            "lighting, colours and visible details. "
            "Use a coherent composition and high visual quality."
        )

        return {
            "status": "success",
            "caption": caption,
            "estimated_prompt": prompt,
            "model": MODEL_NAME,
            "note": (
                "This is an estimated prompt generated from visible "
                "image content, not the original creator prompt."
            )
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }