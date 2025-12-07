# main.py
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from layouts import render_layout, LayoutType
from eink_driver import send_to_display, get_state

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI()

# Serve static files (our dashboard)
app.mount("/static", StaticFiles(directory="static"), name="static")


class DisplayRequest(BaseModel):
    layout: LayoutType
    options: Optional[Dict[str, Any]] = None


@app.get("/", response_class=HTMLResponse)
async def index():
    return Path("static/index.html").read_text()

@app.post("/api/display")
async def set_display(req: DisplayRequest):
    image_path = render_layout(req.layout, req.options or {})
    send_to_display(image_path, req.layout, req.options or {})
    return {"status": "ok", "layout": req.layout, "image_path": str(image_path)}


@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    caption: str = Form(""),
):
    suffix = Path(file.filename).suffix or ".png"
    dest = UPLOAD_DIR / file.filename
    # ensure no overwrite
    i = 1
    while dest.exists():
        dest = UPLOAD_DIR / f"{dest.stem}_{i}{suffix}"
        i += 1

    with dest.open("wb") as f:
        f.write(await file.read())

    return {"image_path": str(dest), "caption": caption}


@app.get("/api/status")
async def status():
    return get_state()


@app.get("/api/preview")
async def preview():
    """
    Returns the last rendered image (if any) so the web UI can show it.
    """
    state = get_state()
    img_path = state.get("current_image")
    if img_path and Path(img_path).exists():
        return FileResponse(img_path, media_type="image/png")
    return {"error": "no image"}
