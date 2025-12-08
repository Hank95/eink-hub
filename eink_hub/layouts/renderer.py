"""Layout rendering engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw

from ..core.config import get_config, LayoutConfig
from ..core.exceptions import WidgetRenderError
from ..core.logging import get_logger
from ..widgets.base import WidgetBounds
from ..widgets.registry import WidgetRegistry

# Import widgets to trigger registration
from ..widgets import clock, text, weather, calendar, strava, todoist, calendar_week, weather_full, indoor_sensor  # noqa: F401

logger = get_logger("layouts.renderer")


class LayoutRenderer:
    """
    Renders layouts by composing widgets onto a canvas.
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 480,
        preview_dir: Path = Path("previews"),
    ) -> None:
        self.width = width
        self.height = height
        self.preview_dir = preview_dir
        self.preview_dir.mkdir(exist_ok=True)

    def render_layout(
        self,
        layout_name: str,
        provider_data: Optional[Dict[str, Dict[str, Any]]] = None,
        layout_config: Optional[LayoutConfig] = None,
    ) -> Path:
        """
        Render a layout by name.

        Args:
            layout_name: Name of layout from config
            provider_data: Dict mapping provider names to their data
            layout_config: Optional layout config override

        Returns:
            Path to the rendered PNG image

        Raises:
            ValueError: If layout is unknown
        """
        if layout_config is None:
            config = get_config()
            layout_config = config.layouts.get(layout_name)

            if not layout_config:
                raise ValueError(f"Unknown layout: {layout_name}")

        # Create canvas (grayscale for rendering, convert to 1-bit for output)
        bg_color = layout_config.background_color
        img = Image.new("L", (self.width, self.height), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Render each widget
        provider_data = provider_data or {}

        for widget_config in layout_config.widgets:
            try:
                bounds = WidgetBounds(
                    x=widget_config.x,
                    y=widget_config.y,
                    width=widget_config.width,
                    height=widget_config.height,
                )

                widget = WidgetRegistry.create_widget(
                    widget_config.type,
                    bounds,
                    widget_config.options,
                )

                # Get provider data for this widget
                provider_name = widget_config.provider or widget.get_required_provider()
                widget_data = provider_data.get(provider_name, {}) if provider_name else None

                widget.render(draw, widget_data)
                logger.debug(f"Rendered widget: {widget_config.type}")

            except Exception as e:
                logger.error(f"Widget render failed: {widget_config.type} - {e}")
                self._render_widget_error(draw, bounds, widget_config.type, str(e))

        # Save
        out_path = self.preview_dir / f"{layout_name}.png"
        img.save(out_path)
        logger.info(f"Rendered layout '{layout_name}' to {out_path}")

        return out_path

    def _render_widget_error(
        self,
        draw: ImageDraw.ImageDraw,
        bounds: WidgetBounds,
        widget_type: str,
        error_msg: str,
    ) -> None:
        """Draw an error placeholder for a failed widget."""
        # Draw border
        draw.rectangle(
            [bounds.x, bounds.y, bounds.x + bounds.width, bounds.y + bounds.height],
            outline=0,
            width=1,
        )

        # Error text
        draw.text(
            (bounds.x + 5, bounds.y + 5),
            f"Error: {widget_type}",
            fill=0,
        )

    def render_preview(
        self,
        layout_name: str,
        provider_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> bytes:
        """
        Render a layout and return PNG bytes (for API preview).

        Args:
            layout_name: Name of layout from config
            provider_data: Dict mapping provider names to their data

        Returns:
            PNG image as bytes
        """
        path = self.render_layout(layout_name, provider_data)
        return path.read_bytes()
