"""FastAPI routes for E-Ink Hub."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import FileResponse

from ..core.config import get_config, reload_config
from ..core.database import get_sensor_db
from ..core.logging import get_logger
from ..core.state import StateManager
from ..core.strava_database import get_strava_db
from .models import (
    DisplayRequest,
    DisplayResponse,
    ModeRequest,
    ProviderStatus,
    StatusResponse,
    SuccessResponse,
    LayoutInfo,
    SensorDataRequest,
    SensorDataResponse,
    SensorReadingResponse,
    ImageInfo,
    ImageListResponse,
    ImagePreviewRequest,
    ImageDisplayRequest,
    ImageDisplayResponse,
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
_rotate_display_callback = None
_rotate_photos_callback = None

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def init_routes(
    state_manager: StateManager,
    scheduler: "HubScheduler",
    renderer: "LayoutRenderer",
    display_driver: "DisplayDriver",
    rotate_display_callback=None,
    rotate_photos_callback=None,
) -> None:
    """Initialize route dependencies."""
    global _state_manager, _scheduler, _renderer, _display_driver
    global _rotate_display_callback, _rotate_photos_callback
    _state_manager = state_manager
    _scheduler = scheduler
    _renderer = renderer
    _display_driver = display_driver
    _rotate_display_callback = rotate_display_callback
    _rotate_photos_callback = rotate_photos_callback


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
    """Switch between manual, auto-rotate, and photo slideshow modes."""
    valid_modes = ("manual", "auto_rotate", "photo_slideshow")
    if req.mode not in valid_modes:
        raise HTTPException(400, f"Mode must be one of: {', '.join(valid_modes)}")

    config = get_config()
    _state_manager.update_display_state(mode=req.mode)

    if req.mode == "manual":
        _scheduler.pause_rotation()
    elif req.mode == "auto_rotate":
        if _rotate_display_callback:
            _scheduler.schedule_display_rotation(
                _rotate_display_callback,
                config.schedule.rotation_interval_minutes,
            )
        _scheduler.resume_rotation()
    elif req.mode == "photo_slideshow":
        if _rotate_photos_callback:
            _scheduler.schedule_display_rotation(
                _rotate_photos_callback,
                config.schedule.photo_interval_minutes,
            )
        _scheduler.resume_rotation()

    logger.info(f"Mode changed to: {req.mode}")

    return SuccessResponse(status="ok", message=f"Mode set to {req.mode}")


@router.post("/refresh/{provider_name}", response_model=SuccessResponse)
async def refresh_provider(provider_name: str, background_tasks: BackgroundTasks):
    """Manually trigger a provider refresh."""
    from ..providers.registry import ProviderRegistry

    config = get_config()

    if provider_name not in config.providers:
        raise HTTPException(404, f"Unknown provider: {provider_name}")

    # Directly fetch and update state instead of relying on scheduler
    provider = ProviderRegistry.get_instance(provider_name)
    if provider:
        try:
            data = await provider.fetch()
            _state_manager.update_provider_state(provider_name, data.data)
            logger.info(f"Provider refreshed directly: {provider_name}")
            return SuccessResponse(status="ok", message=f"Refresh completed for {provider_name}")
        except Exception as e:
            logger.error(f"Provider refresh failed: {provider_name} - {e}")
            _state_manager.update_provider_state(provider_name, {}, error=str(e))
            raise HTTPException(500, f"Refresh failed: {e}")

    raise HTTPException(404, f"Provider instance not found: {provider_name}")


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


# ============================================================================
# ESP32 Sensor Data Endpoints
# ============================================================================


@router.post("/sensor-data", response_model=SensorDataResponse)
@router.post("/weather", response_model=SensorDataResponse, include_in_schema=False)
async def receive_sensor_data(data: SensorDataRequest):
    """
    Receive sensor data from ESP32 sensor (DHT11 or BME280).

    Also aliased as POST /api/weather for ESP32 compatibility.

    Expected JSON payload (BME280):
    {
        "temperature_c": 23.5,
        "humidity": 45.2,
        "pressure_hpa": 1013.25,
        "dew_point_c": 12.3,
        "uptime_s": 3600,
        "boot_count": 5,
        "sensor_id": "esp32_bme280_1"
    }
    """
    try:
        db = get_sensor_db()
        reading_id = db.insert_reading(
            sensor_id=data.sensor_id,
            temperature_c=data.temperature_c,
            humidity=data.humidity,
            pressure_hpa=data.pressure_hpa,
            dew_point_c=data.dew_point_c,
            uptime_s=data.uptime_s,
            boot_count=data.boot_count,
        )

        # Log with pressure if BME280 sensor
        if data.pressure_hpa is not None:
            logger.info(
                f"Sensor data received from {data.sensor_id}: "
                f"{data.temperature_c}°C, {data.humidity}%, {data.pressure_hpa}hPa"
            )
        else:
            logger.info(
                f"Sensor data received from {data.sensor_id}: "
                f"{data.temperature_c}°C, {data.humidity}%"
            )

        return SensorDataResponse(
            status="ok",
            reading_id=reading_id,
            sensor_id=data.sensor_id,
            temperature_c=data.temperature_c,
            humidity=data.humidity,
            pressure_hpa=data.pressure_hpa,
            dew_point_c=data.dew_point_c,
        )
    except Exception as e:
        logger.error(f"Failed to store sensor data: {e}")
        raise HTTPException(500, f"Failed to store sensor data: {e}")


@router.get("/sensor-data", response_model=SensorReadingResponse)
async def get_sensor_data(sensor_id: str = None):
    """Get the latest sensor reading."""
    try:
        db = get_sensor_db()
        reading = db.get_latest_reading(sensor_id)

        if reading is None:
            return SensorReadingResponse(
                available=False,
                error="No sensor data available"
            )

        import datetime as dt

        # Parse timestamp
        timestamp = reading["timestamp"]
        if isinstance(timestamp, str):
            timestamp = dt.datetime.fromisoformat(timestamp)

        # Calculate age
        age_seconds = (dt.datetime.now() - timestamp).total_seconds()
        age_minutes = int(age_seconds / 60)
        is_stale = age_seconds > 300

        # Convert to Fahrenheit
        temp_c = reading["temperature_c"]
        temp_f = (temp_c * 9 / 5) + 32

        # Handle optional BME280 fields
        pressure_hpa = reading.get("pressure_hpa")
        dew_point_c = reading.get("dew_point_c")
        dew_point_f = (dew_point_c * 9 / 5) + 32 if dew_point_c is not None else None
        uptime_s = reading.get("uptime_s")
        boot_count = reading.get("boot_count")

        return SensorReadingResponse(
            available=True,
            sensor_id=reading["sensor_id"],
            temperature_c=round(temp_c, 1),
            temperature_f=round(temp_f, 1),
            humidity=round(reading["humidity"], 1),
            timestamp=timestamp.isoformat(),
            age_minutes=age_minutes,
            is_stale=is_stale,
            pressure_hpa=round(pressure_hpa, 1) if pressure_hpa else None,
            dew_point_c=round(dew_point_c, 1) if dew_point_c else None,
            dew_point_f=round(dew_point_f, 1) if dew_point_f else None,
            uptime_s=uptime_s,
            boot_count=boot_count,
        )
    except Exception as e:
        logger.error(f"Failed to fetch sensor data: {e}")
        raise HTTPException(500, f"Failed to fetch sensor data: {e}")


@router.get("/sensor-data/history")
async def get_sensor_history(sensor_id: str = None, hours: int = 24):
    """Get sensor reading history."""
    try:
        db = get_sensor_db()
        readings = db.get_readings(sensor_id, hours=hours)
        stats = db.get_stats(sensor_id, hours=hours)

        return {
            "readings": readings,
            "stats": stats,
            "hours": hours,
            "sensor_id": sensor_id,
        }
    except Exception as e:
        logger.error(f"Failed to fetch sensor history: {e}")
        raise HTTPException(500, f"Failed to fetch sensor history: {e}")


@router.get("/sensor-data/sensors")
async def list_sensors():
    """List all known sensors."""
    try:
        db = get_sensor_db()
        sensors = db.get_all_sensors()

        # Get latest reading for each sensor
        sensor_info = []
        for sensor_id in sensors:
            reading = db.get_latest_reading(sensor_id)
            if reading:
                sensor_info.append({
                    "sensor_id": sensor_id,
                    "last_reading": reading,
                })

        return {"sensors": sensor_info}
    except Exception as e:
        logger.error(f"Failed to list sensors: {e}")
        raise HTTPException(500, f"Failed to list sensors: {e}")


# ============================================================================
# Image Gallery Endpoints
# ============================================================================


@router.get("/images", response_model=ImageListResponse)
async def list_images():
    """List all uploaded images with metadata."""
    from ..core.image_processor import list_images as get_images

    try:
        images_data = get_images(UPLOAD_DIR)
        images = [ImageInfo(**img) for img in images_data]
        return ImageListResponse(images=images)
    except Exception as e:
        logger.error(f"Failed to list images: {e}")
        raise HTTPException(500, f"Failed to list images: {e}")


@router.get("/images/{filename}")
async def get_image(filename: str):
    """Get an uploaded image file."""
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(404, f"Image not found: {filename}")

    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type)


@router.get("/images/{filename}/thumbnail")
async def get_image_thumbnail(filename: str):
    """Get a thumbnail for an uploaded image."""
    from ..core.image_processor import generate_thumbnail

    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(404, f"Image not found: {filename}")

    try:
        thumbnail_bytes = generate_thumbnail(file_path)
        return Response(content=thumbnail_bytes, media_type="image/jpeg")
    except Exception as e:
        logger.error(f"Failed to generate thumbnail: {e}")
        raise HTTPException(500, f"Failed to generate thumbnail: {e}")


@router.delete("/images/{filename}")
async def delete_image(filename: str):
    """Delete an uploaded image."""
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(404, f"Image not found: {filename}")

    try:
        file_path.unlink()
        logger.info(f"Deleted image: {filename}")
        return SuccessResponse(status="ok", message=f"Deleted {filename}")
    except Exception as e:
        logger.error(f"Failed to delete image: {e}")
        raise HTTPException(500, f"Failed to delete image: {e}")


@router.post("/images/preview")
async def preview_image(req: ImagePreviewRequest):
    """Generate a monochrome preview of an image with rotation and fit options."""
    from ..core.image_processor import generate_preview

    file_path = Path(req.image_path)

    if not file_path.exists():
        raise HTTPException(404, f"Image not found: {req.image_path}")

    # Validate rotation
    if req.rotation not in (0, 90, 180, 270):
        raise HTTPException(400, "Rotation must be 0, 90, 180, or 270")

    # Validate fit mode
    if req.fit_mode not in ("fit", "fill"):
        raise HTTPException(400, "Fit mode must be 'fit' or 'fill'")

    try:
        preview_bytes = generate_preview(file_path, req.rotation, req.fit_mode)
        return Response(content=preview_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Failed to generate preview: {e}")
        raise HTTPException(500, f"Failed to generate preview: {e}")


@router.post("/images/display", response_model=ImageDisplayResponse)
async def display_image(req: ImageDisplayRequest, background_tasks: BackgroundTasks):
    """Process and display an image on the e-ink display."""
    from ..core.image_processor import save_processed_image

    file_path = Path(req.image_path)

    if not file_path.exists():
        raise HTTPException(404, f"Image not found: {req.image_path}")

    # Validate rotation
    if req.rotation not in (0, 90, 180, 270):
        raise HTTPException(400, "Rotation must be 0, 90, 180, or 270")

    # Validate fit mode
    if req.fit_mode not in ("fit", "fill"):
        raise HTTPException(400, "Fit mode must be 'fit' or 'fill'")

    try:
        # Process and save image
        output_path = Path("previews") / "photo_frame.png"
        save_processed_image(file_path, output_path, req.rotation, req.fit_mode)

        # Send to display in background
        background_tasks.add_task(
            _display_driver.send_to_display,
            output_path,
            "photo_frame",
            {"image_path": req.image_path, "rotation": req.rotation, "fit_mode": req.fit_mode},
        )

        logger.info(f"Image display request: {req.image_path}")

        return ImageDisplayResponse(status="ok", image_path=str(output_path))
    except Exception as e:
        logger.error(f"Failed to display image: {e}")
        raise HTTPException(500, f"Failed to display image: {e}")


# ============================================================================
# Strava History Endpoints
# ============================================================================


@router.get("/strava/activities")
async def get_strava_activities(
    activity_type: str = None,
    days: int = None,
    limit: int = 100
):
    """Get stored Strava activities with optional filters."""
    try:
        db = get_strava_db()
        activities = db.get_activities(
            activity_type=activity_type,
            days=days,
            limit=limit
        )
        return {
            "activities": activities,
            "count": len(activities),
            "filters": {
                "activity_type": activity_type,
                "days": days,
                "limit": limit
            }
        }
    except Exception as e:
        logger.error(f"Failed to fetch Strava activities: {e}")
        raise HTTPException(500, f"Failed to fetch Strava activities: {e}")


@router.get("/strava/runs")
async def get_strava_runs(days: int = None, limit: int = 100):
    """Get stored running activities."""
    try:
        db = get_strava_db()
        runs = db.get_runs(days=days, limit=limit)
        return {
            "runs": runs,
            "count": len(runs)
        }
    except Exception as e:
        logger.error(f"Failed to fetch Strava runs: {e}")
        raise HTTPException(500, f"Failed to fetch Strava runs: {e}")


@router.get("/strava/weekly")
async def get_strava_weekly(activity_type: str = "Run", weeks_back: int = 0):
    """
    Get weekly summary for activities.

    Args:
        activity_type: Type of activity (default: Run)
        weeks_back: 0 = current week, 1 = last week, etc.
    """
    try:
        db = get_strava_db()
        summary = db.get_weekly_summary(
            activity_type=activity_type,
            weeks_back=weeks_back
        )
        return summary
    except Exception as e:
        logger.error(f"Failed to fetch Strava weekly summary: {e}")
        raise HTTPException(500, f"Failed to fetch Strava weekly summary: {e}")


@router.get("/strava/monthly")
async def get_strava_monthly(activity_type: str = "Run", months: int = 12):
    """Get monthly mileage totals."""
    try:
        db = get_strava_db()
        totals = db.get_monthly_totals(
            activity_type=activity_type,
            months=months
        )
        return {
            "monthly_totals": totals,
            "activity_type": activity_type
        }
    except Exception as e:
        logger.error(f"Failed to fetch Strava monthly totals: {e}")
        raise HTTPException(500, f"Failed to fetch Strava monthly totals: {e}")


@router.get("/strava/stats")
async def get_strava_stats(activity_type: str = "Run"):
    """Get all-time statistics."""
    try:
        db = get_strava_db()
        stats = db.get_all_time_stats(activity_type=activity_type)
        return {
            "stats": stats,
            "activity_type": activity_type
        }
    except Exception as e:
        logger.error(f"Failed to fetch Strava stats: {e}")
        raise HTTPException(500, f"Failed to fetch Strava stats: {e}")


@router.get("/strava/count")
async def get_strava_count():
    """Get total count of stored activities."""
    try:
        db = get_strava_db()
        count = db.get_activity_count()
        return {"count": count}
    except Exception as e:
        logger.error(f"Failed to fetch Strava count: {e}")
        raise HTTPException(500, f"Failed to fetch Strava count: {e}")
