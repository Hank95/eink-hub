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
