from pathlib import Path
from PIL import Image, ExifTags

PROMPT_KEYS = {
    "prompt",
    "parameters",
    "description",
    "comment",
    "generation_prompt",
    "positive_prompt"
}


def analyze_metadata(file_path):
    path = Path(file_path)

    if not path.exists():
        return {
            "status": "error",
            "message": "File not found."
        }

    result = {
        "status": "success",
        "filename": path.name,
        "file_size_bytes": path.stat().st_size,
        "format": None,
        "width": None,
        "height": None,
        "camera": None,
        "software": None,
        "creation_date": None,
        "embedded_prompt": None,
        "exif_data": {},
        "metadata_available": False,
        "prompt_status": "not_found",
        "prompt_note": (
            "Original prompt cannot be recovered "
            "from pixels alone."
        )
    }

    try:
        with Image.open(path) as image:
            result["format"] = image.format
            result["width"], result["height"] = image.size

            exif = image.getexif()

            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(
                    tag_id, str(tag_id)
                )

                value_text = str(value)[:1000]
                result["exif_data"][tag] = value_text

                if tag in ("Make", "Model"):
                    result["camera"] = value_text

                elif tag == "Software":
                    result["software"] = value_text

                elif tag in (
                    "DateTime",
                    "DateTimeOriginal",
                    "DateTimeDigitized"
                ):
                    result["creation_date"] = value_text

                if tag.lower() in PROMPT_KEYS:
                    result["embedded_prompt"] = value_text

            for key, value in image.info.items():
                key_lower = str(key).lower()

                if (
                    key_lower == "software"
                    and not result["software"]
                ):
                    result["software"] = str(value)[:500]

                if (
                    key_lower in PROMPT_KEYS
                    and not result["embedded_prompt"]
                ):
                    result["embedded_prompt"] = str(value)[:2000]

            result["metadata_available"] = bool(
                exif or image.info
            )

            if result["embedded_prompt"]:
                result["prompt_status"] = "found"

        return result

    except Exception as error:
        result["status"] = "error"
        result["message"] = str(error)
        return result