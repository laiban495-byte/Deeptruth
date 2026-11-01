from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import (
    initialize_database,
    save_scan,
    get_history,
    get_statistics,
    get_scan_by_id,
    delete_scan,
    create_backup,
    list_backups
)

from models.detector import analyze_image
from models.face_detector import analyze_face
from models.video_detector import analyze_video
from models.metadata_detector import analyze_metadata
from models.provenance_detector import analyze_provenance
from models.prompt_generator import generate_image_prompt


ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT / "uploads"
FRONTEND_DIR = ROOT / "frontend"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
ALLOWED = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
MAX_BYTES = 100 * 1024 * 1024

app = FastAPI(title="DeepTruth API", version="2.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def startup():
    initialize_database()
    create_backup()
    print("DeepTruth startup complete.")


@app.get("/health")
def health():
    return {"status": "ok", "app": "DeepTruth", "version": "2.2"}


@app.get("/")
def home():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "DeepTruth API is running."}


if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static"
    )


async def store_upload(file: UploadFile):
    ext = Path(file.filename or "").suffix.lower()

    if ext not in ALLOWED:
        raise HTTPException(400, "Unsupported file type.")

    target = UPLOAD_DIR / f"{uuid4().hex}{ext}"
    total = 0

    try:
        with target.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    raise HTTPException(413, "File exceeds 100 MB limit.")
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if total == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(400, "Empty upload.")

    return target


def persist(path, kind, result):
    record = {
        "filename": path.name,
        "file_path": str(path.relative_to(ROOT)),
        "media_type": kind,
        "result": result
    }
    scan_id = save_scan(record)
    return {"scan_id": scan_id, **record}


def safe_upload_path(relative_path):
    path = (ROOT / relative_path).resolve()
    upload_root = UPLOAD_DIR.resolve()

    if not path.is_relative_to(upload_root):
        raise HTTPException(403, "Invalid media path.")

    return path


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    path = await store_upload(file)
    ext = path.suffix.lower()

    try:
        if ext in IMAGE_EXTENSIONS:
            result = {
                "image_analysis": analyze_image(path),
                "metadata_analysis": analyze_metadata(path),
                "provenance_analysis": analyze_provenance(path)
            }
            kind = "image"

        elif ext in VIDEO_EXTENSIONS:
            result = analyze_video(path)
            result["metadata_analysis"] = {
                "message": "Image EXIF inspection is not available for video."
            }
            result["provenance_analysis"] = analyze_provenance(path)
            kind = "video"

        elif ext in AUDIO_EXTENSIONS:
            from models.audio_detector import analyze_audio
            result = {"audio_analysis": analyze_audio(path)}
            kind = "audio"

        else:
            raise HTTPException(400, "Unsupported media type.")

        return persist(path, kind, result)

    except Exception:
        path.unlink(missing_ok=True)
        raise


@app.post("/analyze/face")
async def face_endpoint(file: UploadFile = File(...)):
    path = await store_upload(file)
    try:
        return persist(path, "face", analyze_face(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise


@app.post("/analyze/video")
async def video_endpoint(file: UploadFile = File(...)):
    path = await store_upload(file)
    try:
        return persist(path, "video", analyze_video(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise


@app.post("/analyze/provenance")
async def provenance_endpoint(file: UploadFile = File(...)):
    path = await store_upload(file)
    try:
        return persist(path, "provenance", analyze_provenance(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise


@app.post("/generate-prompt")
async def generate_prompt_upload(file: UploadFile = File(...)):
    path = await store_upload(file)

    try:
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise HTTPException(400, "Please upload an image.")

        result = generate_image_prompt(path)

        if result.get("status") != "success":
            raise HTTPException(
                500,
                result.get("message", "Prompt generation failed.")
            )

        return result
    finally:
        path.unlink(missing_ok=True)


@app.get("/history")
def history(limit: int = 50):
    return get_history(max(1, min(limit, 200)))


@app.get("/history/{scan_id}")
def history_item(scan_id: int):
    item = get_scan_by_id(scan_id)
    if item is None:
        raise HTTPException(404, "Investigation not found.")
    return item


@app.delete("/history/{scan_id}")
def delete_history_item(scan_id: int):
    item = delete_scan(scan_id)

    if item is None:
        raise HTTPException(404, "Investigation not found.")

    relative_path = item.get("file_path")
    if relative_path:
        path = safe_upload_path(relative_path)
        path.unlink(missing_ok=True)

    return {
        "status": "success",
        "message": "Investigation deleted.",
        "scan_id": scan_id
    }


@app.get("/media/{scan_id}")
def get_scan_media(scan_id: int):
    item = get_scan_by_id(scan_id)

    if item is None or not item.get("file_path"):
        raise HTTPException(404, "Media not found.")

    path = safe_upload_path(item["file_path"])

    if not path.is_file():
        raise HTTPException(404, "Uploaded media file not found.")

    return FileResponse(path)


@app.get("/statistics")
def statistics():
    return get_statistics()


@app.post("/backup")
def backup():
    return {"backup": create_backup()}


@app.get("/backups")
def backups():
    return {"backups": list_backups()}