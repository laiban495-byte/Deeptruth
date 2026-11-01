from pathlib import Path

import numpy as np
import soundfile as sf
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from scipy.signal import resample_poly

MODEL_REPO = "ayush2635/Dhwani-Multilingual-Deepfake-Audio-Detection-Model"
MODEL_FILE = "best_model.onnx"

_session = None


def load_audio_detector():
    global _session

    if _session is None:
        model_path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE
        )

        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 2

        _session = ort.InferenceSession(
            model_path,
            sess_options=options,
            providers=["CPUExecutionProvider"]
        )

    return _session


def prepare_audio(audio_path):
    audio, sample_rate = sf.read(
        str(audio_path),
        dtype="float32",
        always_2d=True
    )

    # Convert stereo to mono
    audio = np.mean(audio, axis=1)

    if sample_rate != 16000:
        audio = resample_poly(
            audio,
            16000,
            sample_rate
        ).astype(np.float32)

    return audio


def analyze_audio(audio_path):
    try:
        path = Path(audio_path)

        if not path.exists():
            return {
                "status": "error",
                "message": "Audio file not found."
            }

        audio = prepare_audio(path)

        if len(audio) < 1600:
            return {
                "status": "error",
                "message": "Audio is too short for reliable analysis."
            }

        session = load_audio_detector()
        input_name = session.get_inputs()[0].name

        window_size = 48000
        scores = []

        # Analyze 3-second windows
        for start in range(0, len(audio), window_size):
            chunk = audio[start:start + window_size]

            if len(chunk) < 1600:
                continue

            if len(chunk) < window_size:
                chunk = np.pad(
                    chunk,
                    (0, window_size - len(chunk))
                )

            chunk = (
                chunk - np.mean(chunk)
            ) / np.sqrt(np.var(chunk) + 1e-5)

            chunk = chunk.astype(
                np.float32
            ).reshape(1, window_size)

            logits = session.run(
                None,
                {input_name: chunk}
            )[0]

            logits = logits[0].astype(np.float64)
            logits -= np.max(logits)

            probabilities = np.exp(logits)
            probabilities /= np.sum(probabilities)

            scores.append(float(probabilities[1]))

        if not scores:
            return {
                "status": "error",
                "message": "No usable audio segments found."
            }

        fake_probability = float(np.mean(scores))
        real_probability = 1.0 - fake_probability

        if fake_probability >= 0.65:
            verdict = "likely-ai-generated"
        elif fake_probability <= 0.35:
            verdict = "likely-real"
        else:
            verdict = "inconclusive"

        return {
            "status": "success",
            "verdict": verdict,
            "ai_voice_probability": round(
                fake_probability * 100, 2
            ),
            "real_voice_probability": round(
                real_probability * 100, 2
            ),
            "segments_analyzed": len(scores),
            "model": MODEL_REPO,
            "analysis_note": (
                "Multilingual audio deepfake model. "
                "Results are probabilistic, not proof."
            )
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }