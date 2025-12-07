"""Abstract base class for display widgets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel


class WidgetBounds(BaseModel):
    """Widget position and size."""

    x: int
    y: int
    width: int
    height: int


class BaseWidget(ABC):
    """
    Abstract base class for all display widgets.

    A widget:
    - Renders a rectangular region of the display
    - Receives data from a provider
    - Handles its own layout within its bounds
    """

    name: str  # Widget type identifier

    # Common font paths to try
    FONT_PATHS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "/System/Library/Fonts/HelveticaNeue.ttc",  # macOS
    ]

    BOLD_FONT_PATHS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
    ]

    def __init__(
        self,
        bounds: WidgetBounds,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.bounds = bounds
        self.options = options or {}
        self._font_cache: Dict[Tuple[int, bool], ImageFont.FreeTypeFont] = {}

    @abstractmethod
    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Render the widget onto the provided ImageDraw context.

        Args:
            draw: PIL ImageDraw to render onto
            data: Provider data for this widget
        """
        pass

    def get_required_provider(self) -> Optional[str]:
        """
        Return the provider type this widget needs, or None.

        Override in subclasses that require provider data.
        """
        return None

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """
        Load a font with fallback handling.

        Args:
            size: Font size in points
            bold: Whether to use bold variant

        Returns:
            Loaded font or default font
        """
        cache_key = (size, bold)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font_paths = self.BOLD_FONT_PATHS if bold else self.FONT_PATHS

        for path in font_paths:
            try:
                font = ImageFont.truetype(path, size)
                self._font_cache[cache_key] = font
                return font
            except Exception:
                continue

        # Fallback to default
        font = ImageFont.load_default()
        self._font_cache[cache_key] = font
        return font

    def _text_size(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
    ) -> Tuple[int, int]:
        """
        Get text dimensions (Pillow 10+ compatible).

        Args:
            draw: ImageDraw context
            text: Text to measure
            font: Font to use

        Returns:
            (width, height) tuple
        """
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def _draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        y: int,
        fill: int = 0,
    ) -> None:
        """
        Draw horizontally centered text within widget bounds.

        Args:
            draw: ImageDraw context
            text: Text to draw
            font: Font to use
            y: Y position for text
            fill: Fill color (0=black, 255=white)
        """
        w, _ = self._text_size(draw, text, font)
        x = self.bounds.x + (self.bounds.width - w) // 2
        draw.text((x, y), text, font=font, fill=fill)

    def _truncate_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
        suffix: str = "...",
    ) -> str:
        """
        Truncate text to fit within max_width.

        Args:
            draw: ImageDraw context
            text: Text to potentially truncate
            font: Font to use
            max_width: Maximum width in pixels
            suffix: Suffix to add when truncating

        Returns:
            Original or truncated text
        """
        w, _ = self._text_size(draw, text, font)
        if w <= max_width:
            return text

        suffix_w, _ = self._text_size(draw, suffix, font)
        target_width = max_width - suffix_w

        while len(text) > 0:
            text = text[:-1]
            w, _ = self._text_size(draw, text, font)
            if w <= target_width:
                return text.rstrip() + suffix

        return suffix

    def _draw_border(
        self,
        draw: ImageDraw.ImageDraw,
        padding: int = 0,
        width: int = 1,
    ) -> None:
        """
        Draw a border around the widget (useful for debugging layout).

        Args:
            draw: ImageDraw context
            padding: Padding inside the border
            width: Border line width
        """
        draw.rectangle(
            [
                self.bounds.x + padding,
                self.bounds.y + padding,
                self.bounds.x + self.bounds.width - padding,
                self.bounds.y + self.bounds.height - padding,
            ],
            outline=0,
            width=width,
        )

    def _render_no_data(
        self,
        draw: ImageDraw.ImageDraw,
        message: str = "No data",
    ) -> None:
        """
        Render a placeholder when no data is available.

        Args:
            draw: ImageDraw context
            message: Message to display
        """
        font = self._load_font(14)
        y = self.bounds.y + self.bounds.height // 2 - 7
        self._draw_centered_text(draw, message, font, y, fill=128)
