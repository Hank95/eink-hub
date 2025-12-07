"""FastAPI routes for E-Ink Hub."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from ..core.config import get_config, reload_config
from ..core.logging import get_logger
from ..core.state import StateManager
from .models import (
    DisplayRequest,
    DisplayResponse,
    ModeRequest,
    ProviderStatus,
    StatusResponse,
    SuccessResponse,
    LayoutInfo,
)

if TYPE_CHECKING:
    from ..core.scheduler import HubScheduler
    from ..layouts.renderer import LayoutRenderer
    from ..display.driver import DisplayDriver

logger = get_logger("api.routes")

router = APIRouter(prefix="/api")

# These will be set during app startup
_state_manager: StateManager = None
_scheduler: "HubScheduler" = None
_renderer: "LayoutRenderer" = None
_display_driver: "DisplayDriver" = None

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def init_routes(
    state_manager: StateManager,
    scheduler: "HubScheduler",
    renderer: "LayoutRenderer",
    display_driver: "DisplayDriver",
) -> None:
    """Initialize route dependencies."""
    global _state_manager, _scheduler, _renderer, _display_driver
    _state_manager = state_manager
    _scheduler = scheduler
    _renderer = renderer
    _display_driver = display_driver


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current display status and available layouts."""
    state = _state_manager.get_state()
    config = get_config()

    providers = []
    for name, prov_config in config.providers.items():
        prov_state = state.providers.get(name)
        providers.append(
            ProviderStatus(
                name=name,
                enabled=prov_config.enabled,
                last_fetch=(
                    prov_state.last_fetch.isoformat()
                    if prov_state and prov_state.last_fetch
                    else None
                ),
                error=prov_state.error if prov_state else None,
                refresh_interval_minutes=prov_config.refresh_interval_minutes,
            )
        )

    return StatusResponse(
        current_layout=state.display.current_layout,
        current_image=state.display.current_image,
        last_updated=(
            state.display.last_updated.isoformat()
            if state.display.last_updated
            else None
        ),
        mode=state.display.mode,
        available_layouts=list(config.layouts.keys()),
        providers=providers,
    )


@router.post("/display", response_model=DisplayResponse)
async def set_display(req: DisplayRequest, background_tasks: BackgroundTasks):
    """Render and display a specific layout."""
    config = get_config()

    if req.layout not in config.layouts:
        raise HTTPException(404, f"Unknown layout: {req.layout}")

    # Gather provider data
    provider_data = _state_manager.get_all_provider_data()

    # Render
    image_path = _renderer.render_layout(req.layout, provider_data)

    # Send to display in background
    background_tasks.add_task(
        _display_driver.send_to_display,
        image_path,
        req.layout,
        req.options,
    )

    logger.info(f"Display request: {req.layout}")

    return DisplayResponse(
        status="ok",
        layout=req.layout,
        image_path=str(image_path),
    )


@router.post("/mode", response_model=SuccessResponse)
async def set_mode(req: ModeRequest):
    """Switch between manual and auto-rotate mode."""
    if req.mode not in ("manual", "auto_rotate"):
        raise HTTPException(400, "Mode must be 'manual' or 'auto_rotate'")

    _state_manager.update_display_state(mode=req.mode)

    if req.mode == "manual":
        _scheduler.pause_rotation()
    else:
        _scheduler.resume_rotation()

    logger.info(f"Mode changed to: {req.mode}")

    return SuccessResponse(status="ok", message=f"Mode set to {req.mode}")


@router.post("/refresh/{provider_name}", response_model=SuccessResponse)
async def refresh_provider(provider_name: str):
    """Manually trigger a provider refresh."""
    config = get_config()

    if provider_name not in config.providers:
        raise HTTPException(404, f"Unknown provider: {provider_name}")

    _scheduler.trigger_now(f"provider_{provider_name}")
    logger.info(f"Manual refresh triggered: {provider_name}")

    return SuccessResponse(status="ok", message=f"Refresh triggered for {provider_name}")


@router.post("/reload-config", response_model=SuccessResponse)
async def api_reload_config():
    """Hot-reload configuration from disk."""
    try:
        reload_config()
        logger.info("Configuration reloaded via API")
        return SuccessResponse(status="ok", message="Configuration reloaded")
    except Exception as e:
        logger.error(f"Config reload failed: {e}")
        raise HTTPException(500, f"Config reload failed: {e}")


@router.get("/layouts")
async def list_layouts():
    """List all available layouts."""
    config = get_config()
    return {
        name: LayoutInfo(
            name=layout.name or name,
            widget_count=len(layout.widgets),
        )
        for name, layout in config.layouts.items()
    }


@router.get("/providers")
async def list_providers():
    """List all configured providers."""
    config = get_config()
    state = _state_manager.get_state()

    result = {}
    for name, prov_config in config.providers.items():
        prov_state = state.providers.get(name)
        result[name] = ProviderStatus(
            name=name,
            enabled=prov_config.enabled,
            last_fetch=(
                prov_state.last_fetch.isoformat()
                if prov_state and prov_state.last_fetch
                else None
            ),
            error=prov_state.error if prov_state else None,
            refresh_interval_minutes=prov_config.refresh_interval_minutes,
        )

    return result


@router.get("/jobs")
async def list_jobs():
    """List all scheduled jobs."""
    return {"jobs": _scheduler.list_jobs()}


@router.get("/preview")
async def get_preview():
    """Get the current preview image."""
    state = _state_manager.get_state()
    img_path = state.display.current_image

    if img_path and Path(img_path).exists():
        return FileResponse(img_path, media_type="image/png")

    raise HTTPException(404, "No preview image available")


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    caption: str = Form(""),
):
    """Upload an image for photo frame layout."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    suffix = Path(file.filename).suffix or ".png"
    dest = UPLOAD_DIR / file.filename

    # Avoid overwrite
    i = 1
    while dest.exists():
        stem = Path(file.filename).stem
        dest = UPLOAD_DIR / f"{stem}_{i}{suffix}"
        i += 1

    content = await file.read()
    dest.write_bytes(content)

    logger.info(f"Image uploaded: {dest}")

    return {"image_path": str(dest), "caption": caption}
