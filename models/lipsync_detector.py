from pathlib import Path
import subprocess
import os
import re

SYNCNET_DIR = Path(
    os.environ.get(
        "DEEPTRUTH_SYNCNET_DIR",
        "external/syncnet_python"
    )
).resolve()

DATA_DIR = Path("reports/syncnet_temp").resolve()


def analyze_lipsync(video_path):
    video_path = Path(video_path).resolve()

    if not video_path.exists():
        return {
            "status": "error",
            "message": "Video file not found."
        }

    script = SYNCNET_DIR / "run_syncnet.py"

    if not script.exists():
        return {
            "status": "not_configured",
            "message": (
                "SyncNet repository or pretrained weights "
                "are not installed. Configure "
                "DEEPTRUTH_SYNCNET_DIR first."
            )
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    reference = video_path.stem

    command = [
        "python",
        str(script),
        "--videofile", str(video_path),
        "--reference", reference,
        "--data_dir", str(DATA_DIR)
    ]

    try:
        result = subprocess.run(
            command,
            cwd=str(SYNCNET_DIR),
            capture_output=True,
            text=True,
            timeout=900
        )

        output = (result.stdout or "") + "\n" + (
            result.stderr or ""
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "message": "SyncNet analysis failed.",
                "details": output[-3000:]
            }

        offset_match = re.search(
            r"AV offset:\s*(-?\d+)",
            output,
            re.IGNORECASE
        )

        confidence_match = re.search(
            r"Confidence:\s*([0-9.]+)",
            output,
            re.IGNORECASE
        )

        if not offset_match:
            return {
                "status": "inconclusive",
                "message": (
                    "SyncNet ran, but its output could not "
                    "be interpreted automatically."
                ),
                "details": output[-3000:]
            }

        offset = int(offset_match.group(1))
        confidence = (
            float(confidence_match.group(1))
            if confidence_match else None
        )

        return {
            "status": "success",
            "av_offset_frames": offset,
            "syncnet_confidence": confidence,
            "interpretation": (
                "Audio-video offset estimated. "
                "A non-zero offset alone does not prove manipulation."
            ),
            "model": "SyncNet"
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "SyncNet timed out."
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }