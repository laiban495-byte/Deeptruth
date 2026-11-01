from pathlib import Path
import cv2
import numpy as np


def analyze_video_forensics(video_path, max_frames=300):
    path = Path(video_path)

    if not path.exists():
        return {
            "status": "error",
            "message": "Video file not found."
        }

    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        return {
            "status": "error",
            "message": "Could not open video."
        }

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    duration = (
        total_frames / fps
        if fps and fps > 0 else 0
    )

    sample_step = max(
        1,
        total_frames // max_frames
    )

    previous = None
    differences = []
    duplicate_frames = []
    sampled = 0
    frame_index = 0

    while True:
        ok, frame = cap.read()

        if not ok:
            break

        if frame_index % sample_step == 0:
            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            gray = cv2.resize(
                gray,
                (160, 90)
            )

            if previous is not None:
                difference = float(
                    np.mean(
                        cv2.absdiff(previous, gray)
                    )
                )

                differences.append(difference)

                if difference < 0.35:
                    duplicate_frames.append(frame_index)

            previous = gray
            sampled += 1

        frame_index += 1

    cap.release()

    if not differences:
        return {
            "status": "inconclusive",
            "message": "Not enough frames to compare."
        }

    values = np.array(
        differences,
        dtype=np.float32
    )

    median = float(np.median(values))
    mean = float(np.mean(values))
    std = float(np.std(values))

    # Flag unusually large visual transitions.
    threshold = mean + (3 * std)

    abrupt_changes = [
        index
        for index, value in enumerate(values)
        if value > threshold and std > 0
    ]

    findings = []

    if duplicate_frames:
        findings.append({
            "type": "duplicate_or_frozen_frames",
            "count": len(duplicate_frames),
            "sample_frame_numbers": duplicate_frames[:20]
        })

    if abrupt_changes:
        findings.append({
            "type": "unusual_frame_transitions",
            "count": len(abrupt_changes),
            "sample_positions": abrupt_changes[:20]
        })

    return {
        "status": "success",
        "video_info": {
            "duration_seconds": round(duration, 2),
            "fps": round(fps, 2) if fps else None,
            "total_frames": total_frames,
            "resolution": f"{width}x{height}"
        },
        "frames_sampled": sampled,
        "duplicate_or_frozen_frame_count": len(
            duplicate_frames
        ),
        "abrupt_transition_count": len(abrupt_changes),
        "frame_difference": {
            "mean": round(mean, 3),
            "median": round(median, 3),
            "standard_deviation": round(std, 3)
        },
        "findings": findings,
        "verdict": (
            "review-recommended"
            if findings else "no-obvious-anomaly"
        ),
        "analysis_note": (
            "Heuristic forensic checks only. "
            "Normal scene cuts, static scenes and compression "
            "can also cause these signals."
        )
    }