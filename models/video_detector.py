from pathlib import Path
import tempfile
import subprocess

from models.face_detector import analyze_face
from models.audio_detector import analyze_audio
from models.lipsync_detector import analyze_lipsync
from models.video_forensics import analyze_video_forensics


def analyze_video_frames(video_path, max_frames=16):
    try:
        import cv2
        import numpy as np

        path = Path(video_path)
        cap = cv2.VideoCapture(str(path))

        if not cap.isOpened():
            return {
                "status": "error",
                "message": "Could not open video."
            }

        total = int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        if total <= 0:
            cap.release()
            return {
                "status": "error",
                "message": "No readable frames."
            }

        positions = np.linspace(
            0,
            total - 1,
            min(max_frames, total),
            dtype=int
        )

        scores = []
        checked = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            for number, position in enumerate(positions):
                cap.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    int(position)
                )

                ok, frame = cap.read()

                if not ok:
                    continue

                frame_path = (
                    Path(temp_dir) / f"frame_{number}.jpg"
                )

                if not cv2.imwrite(
                    str(frame_path), frame
                ):
                    continue

                result = analyze_face(frame_path)
                checked += 1

                if result.get("status") != "success":
                    continue

                fake = next(
                    (
                        item
                        for item in result.get(
                            "predictions", []
                        )
                        if (
                            "fake" in item["label"].lower()
                            or "deepfake" in item["label"].lower()
                        )
                    ),
                    None
                )

                if fake:
                    scores.append(float(fake["score"]))

        cap.release()

        if not scores:
            return {
                "status": "not_configured",
                "message": (
                    "Classifier has no recognized fake class label. "
                    "Video verdict withheld."
                ),
                "frames_checked": checked
            }

        score = float(np.mean(scores))

        if score >= 0.70:
            verdict = "likely-deepfake"
        elif score <= 0.30:
            verdict = "likely-real"
        else:
            verdict = "inconclusive"

        return {
            "status": "success",
            "verdict": verdict,
            "fake_frame_score_percent": round(
                score * 100, 2
            ),
            "frames_scored": len(scores),
            "analysis_note": (
                "Sampled image classifier, not a dedicated "
                "temporal video model."
            )
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }


def extract_audio(video_path, output_path):
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-vn",
                "-ac", "1",
                "-ar", "16000",
                "-c:a", "pcm_s16le",
                str(output_path)
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        return result.returncode == 0

    except (
        FileNotFoundError,
        subprocess.TimeoutExpired
    ):
        return False


def analyze_video(video_path):
    path = Path(video_path)

    if not path.exists():
        return {
            "status": "error",
            "message": "Video file not found."
        }

    visual = analyze_video_frames(path)
    integrity = analyze_video_forensics(path)
    lipsync = analyze_lipsync(path)

    audio = {
        "status": "not_available",
        "verdict": "not_available",
        "message": (
            "Audio extraction failed. Install FFmpeg "
            "and add it to PATH."
        )
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "audio.wav"

        if extract_audio(path, audio_path) and audio_path.exists():
            audio = analyze_audio(audio_path)

    return {
        "status": "success",
        "media_type": "video",
        "visual_deepfake_analysis": visual,
        "audio_analysis": audio,
        "lip_sync_analysis": lipsync,
        "video_integrity_analysis": integrity,
        "overall_assessment": (
            "Review each component separately. "
            "No individual score proves manipulation."
        )
    }