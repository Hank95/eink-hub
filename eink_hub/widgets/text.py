"""Generic text widget."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("text")
class TextWidget(BaseWidget):
    """
    Generic text display widget.

    Options:
    - text: str - Text to display (required)
    - font_size: int (default: 20)
    - bold: bool (default: False)
    - center: bool (default: False) - Center horizontally
    - wrap: bool (default: False) - Wrap text to multiple lines
    """

    name = "text"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render the text widget."""
        text = self.options.get("text", "")
        if not text:
            return

        font_size = self.options.get("font_size", 20)
        bold = self.options.get("bold", False)
        center = self.options.get("center", False)
        wrap = self.options.get("wrap", False)

        font = self._load_font(font_size, bold=bold)

        if wrap:
            self._render_wrapped(draw, text, font, center)
        elif center:
            y = self.bounds.y + (self.bounds.height - font_size) // 2
            self._draw_centered_text(draw, text, font, y)
        else:
            draw.text((self.bounds.x, self.bounds.y), text, font=font, fill=0)

    def _render_wrapped(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font,
        center: bool,
    ) -> None:
        """Render text with word wrapping."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            w, _ = self._text_size(draw, test_line, font)

            if w <= self.bounds.width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        # Render lines
        line_height = self.options.get("font_size", 20) + 4
        y = self.bounds.y

        for line in lines:
            if y + line_height > self.bounds.y + self.bounds.height:
                break

            if center:
                self._draw_centered_text(draw, line, font, y)
            else:
                draw.text((self.bounds.x, y), line, font=font, fill=0)

            y += line_height

    def get_required_provider(self) -> Optional[str]:
        return None
