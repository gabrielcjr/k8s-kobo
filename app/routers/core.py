import os
import urllib.parse
from datetime import datetime, timezone
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse

from ..config import STATIC_DIR

router = APIRouter(tags=["Core"])

@router.get("/healthz")
def healthz():
    return {"status": "ok", "app": "kobo-renovame", "time": datetime.now(timezone.utc).isoformat()}

@router.get("/sw.js")
@router.get("/x/offline-app-worker.js")
def get_service_worker():
    sw_path = os.path.join(STATIC_DIR, "sw.js")
    if not os.path.exists(sw_path):
        raise HTTPException(status_code=404, detail="Service worker not found")
    with open(sw_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/javascript; charset=utf-8",
        headers={
            "Content-Type": "application/javascript; charset=utf-8",
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

@router.get("/manifest.json")
def get_manifest_json():
    manifest_path = os.path.join(STATIC_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="Manifest not found")
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/manifest+json; charset=utf-8",
        headers={
            "Content-Type": "application/manifest+json; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    )

@router.get("/media/{filename}")
def get_media(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(file_path):
        unescaped = urllib.parse.unquote(filename)
        file_path = os.path.join(STATIC_DIR, unescaped)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Media file not found")
    media_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    return StreamingResponse(open(file_path, "rb"), media_type=media_type)

@router.get("/media/get/0/PY2hbkKi/{hash_val}/{filename}")
def get_media_enketo_style(hash_val: str, filename: str):
    return get_media(filename)
