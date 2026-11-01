from pathlib import Path


def analyze_provenance(file_path):
    path = Path(file_path)

    if not path.exists():
        return {
            "status": "error",
            "message": "Media file not found."
        }

    try:
        from c2pa import Reader

        with Reader(str(path)) as reader:
            manifest_json = reader.json()

        import json

        if isinstance(manifest_json, str):
            manifest = json.loads(manifest_json)
        else:
            manifest = manifest_json

        active = manifest.get("active_manifest")
        manifests = manifest.get("manifests", {})

        active_manifest = (
            manifests.get(active, {})
            if active else {}
        )

        if not active_manifest:
            return {
                "status": "success",
                "provenance_found": False,
                "verification": "no_manifest_found",
                "message": (
                    "No readable C2PA manifest was found. "
                    "This does not mean the media is fake."
                )
            }

        return {
            "status": "success",
            "provenance_found": True,
            "verification": "manifest_read",
            "active_manifest": active,
            "claim_generator": active_manifest.get(
                "claim_generator"
            ),
            "title": active_manifest.get("title"),
            "format": active_manifest.get("format"),
            "manifest": active_manifest,
            "message": (
                "C2PA manifest found. Review validation "
                "status and signing information before "
                "treating it as verified."
            )
        }

    except ImportError:
        return {
            "status": "not_configured",
            "message": (
                "Install the c2pa Python package to enable "
                "provenance verification."
            )
        }

    except Exception as error:
        return {
            "status": "success",
            "provenance_found": False,
            "verification": "unavailable_or_invalid",
            "message": str(error)
        }