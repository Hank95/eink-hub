"""Pydantic models for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DisplayRequest(BaseModel):
    """Request to display a layout."""

    layout: str
    options: Optional[Dict[str, Any]] = None


class ModeRequest(BaseModel):
    """Request to change display mode."""

    mode: str  # "manual" | "auto_rotate"


class ProviderStatus(BaseModel):
    """Status of a single provider."""

    name: str
    enabled: bool
    last_fetch: Optional[str] = None
    error: Optional[str] = None
    refresh_interval_minutes: int


class LayoutInfo(BaseModel):
    """Information about a layout."""

    name: str
    widget_count: int


class StatusResponse(BaseModel):
    """Full status response."""

    current_layout: Optional[str] = None
    current_image: Optional[str] = None
    last_updated: Optional[str] = None
    mode: str
    available_layouts: List[str]
    providers: List[ProviderStatus]


class LayoutListResponse(BaseModel):
    """Response listing available layouts."""

    layouts: Dict[str, LayoutInfo]


class ProviderListResponse(BaseModel):
    """Response listing configured providers."""

    providers: Dict[str, ProviderStatus]


class JobsResponse(BaseModel):
    """Response listing scheduled jobs."""

    jobs: Dict[str, str]  # job_name -> next_run_time


class SuccessResponse(BaseModel):
    """Generic success response."""

    status: str = "ok"
    message: Optional[str] = None


class DisplayResponse(BaseModel):
    """Response after updating display."""

    status: str = "ok"
    layout: str
    image_path: str


class ErrorResponse(BaseModel):
    """Error response."""

    status: str = "error"
    message: str


class SensorDataRequest(BaseModel):
    """Request to submit sensor data from ESP32."""

    temperature_c: float
    humidity: float
    sensor_id: str = "esp32_dht11_1"


class SensorDataResponse(BaseModel):
    """Response after receiving sensor data."""

    status: str = "ok"
    reading_id: int
    sensor_id: str
    temperature_c: float
    humidity: float


class SensorReadingResponse(BaseModel):
    """Response with sensor reading data."""

    available: bool
    sensor_id: Optional[str] = None
    temperature_c: Optional[float] = None
    temperature_f: Optional[float] = None
    humidity: Optional[float] = None
    timestamp: Optional[str] = None
    age_minutes: Optional[int] = None
    is_stale: Optional[bool] = None
    error: Optional[str] = None


# ============================================================================
# Image Gallery Models
# ============================================================================


class ImageInfo(BaseModel):
    """Metadata for an uploaded image."""

    filename: str
    path: str
    size_bytes: int
    width: int
    height: int
    uploaded_at: str


class ImageListResponse(BaseModel):
    """Response listing uploaded images."""

    images: List[ImageInfo]


class ImagePreviewRequest(BaseModel):
    """Request to generate an image preview."""

    image_path: str
    rotation: int = 0  # 0, 90, 180, 270
    fit_mode: str = "fit"  # "fit" or "fill"


class ImageDisplayRequest(BaseModel):
    """Request to display an image on the e-ink display."""

    image_path: str
    rotation: int = 0
    fit_mode: str = "fit"


class ImageDisplayResponse(BaseModel):
    """Response after displaying an image."""

    status: str = "ok"
    image_path: str
