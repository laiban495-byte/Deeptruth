"""
DeepTruth - Face Manipulation Detector
Detects suspicious/manipulated face images using a pretrained ViT model.

Model: hamzenium/ViT-Deepfake-Classifier
Device: CPU
"""

from functools import lru_cache

import cv2
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification


MODEL_NAME = "hamzenium/ViT-Deepfake-Classifier"
FAKE_THRESHOLD = 0.65
INCONCLUSIVE_LOW = 0.45


@lru_cache(maxsize=1)
def load_detector():
    """Load the model once and reuse it."""

    processor = AutoImageProcessor.from_pretrained(MODEL_NAME)

    model = AutoModelForImageClassification.from_pretrained(
        MODEL_NAME
    )

    model.to("cpu")
    model.eval()

    return processor, model


def detect_faces(image):
    """Find faces and return expanded face crops."""

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    cascade_path = (
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    face_cascade = cv2.CascadeClassifier(cascade_path)

    boxes = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(45, 45)
    )

    height, width = image.shape[:2]
    results = []

    for x, y, w, h in boxes:

        margin_x = int(w * 0.25)
        margin_y = int(h * 0.25)

        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(width, x + w + margin_x)
        y2 = min(height, y + h + margin_y)

        crop = image[y1:y2, x1:x2]

        if crop.size == 0:
            continue

        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        results.append({
            "box": {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            },
            "image": Image.fromarray(crop_rgb)
        })

    return results


def classify_face(face_image, processor, model):
    """Classify one face crop."""

    inputs = processor(
        images=face_image,
        return_tensors="pt"
    )

    with torch.inference_mode():
        outputs = model(**inputs)
        probabilities = torch.softmax(
            outputs.logits,
            dim=-1
        )[0]

    labels = model.config.id2label

    fake_index = None
    real_index = None

    for index in range(len(probabilities)):
        label = str(labels.get(index, "")).lower()

        if any(word in label for word in ["fake", "deepfake", "manipulated"]):
            fake_index = index

        if any(word in label for word in ["real", "authentic"]):
            real_index = index

    # This model card documents index 0 = real, index 1 = fake.
    if fake_index is None:
        fake_index = 1

    if real_index is None:
        real_index = 0

    fake_probability = float(probabilities[fake_index])
    real_probability = float(probabilities[real_index])

    if fake_probability >= FAKE_THRESHOLD:
        verdict = "SUSPICIOUS_MANIPULATED_FACE"

    elif fake_probability <= INCONCLUSIVE_LOW:
        verdict = "NO_STRONG_MANIPULATION_SIGNAL"

    else:
        verdict = "INCONCLUSIVE"

    return {
        "verdict": verdict,
        "fake_probability": round(fake_probability * 100, 2),
        "real_probability": round(real_probability * 100, 2)
    }


def analyze_face_manipulation(image_path):
    """
    Analyze every detected face in an image.

    Returns a structured result for the DeepTruth backend.
    """

    try:
        image = cv2.imread(str(image_path))

        if image is None:
            return {
                "status": "error",
                "message": "Could not read the image."
            }

        faces = detect_faces(image)

        if not faces:
            return {
                "status": "inconclusive",
                "verdict": "NO_FACE_DETECTED",
                "face_count": 0,
                "faces": [],
                "message": (
                    "No detectable face was found. "
                    "Face manipulation analysis could not be performed."
                )
            }

        processor, model = load_detector()

        face_results = []

        for number, face in enumerate(faces, start=1):

            prediction = classify_face(
                face["image"],
                processor,
                model
            )

            face_results.append({
                "face_number": number,
                "box": face["box"],
                **prediction
            })

        suspicious_faces = [
            face for face in face_results
            if face["verdict"] == "SUSPICIOUS_MANIPULATED_FACE"
        ]

        inconclusive_faces = [
            face for face in face_results
            if face["verdict"] == "INCONCLUSIVE"
        ]

        if suspicious_faces:
            overall_verdict = "POSSIBLE_AI_MANIPULATION"
            status = "success"

        elif inconclusive_faces:
            overall_verdict = "INCONCLUSIVE"
            status = "inconclusive"

        else:
            overall_verdict = "NO_STRONG_MANIPULATION_SIGNAL"
            status = "success"

        return {
            "status": status,
            "verdict": overall_verdict,
            "face_count": len(face_results),
            "suspicious_face_count": len(suspicious_faces),
            "faces": face_results,
            "model": MODEL_NAME,
            "message": (
                "Face-level manipulation screening completed. "
                "This is a model prediction, not proof of a face swap."
            )
        }

    except Exception as error:
        return {
            "status": "error",
            "verdict": "INCONCLUSIVE",
            "message": str(error)
        }.\venv312\Scripts\Activate.ps1
