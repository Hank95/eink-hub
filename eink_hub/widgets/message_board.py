"""Message board widget for displaying Larry's messages."""

from __future__ import annotations

import datetime as dt
import textwrap
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont

from ..core.logging import get_logger
from .base import BaseWidget
from .registry import WidgetRegistry

logger = get_logger("widgets.message_board")


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default if needed."""
    try:
        weight = "Bold" if bold else "Regular"
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVuSans-{weight}.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()


@WidgetRegistry.register("message_board")
class MessageBoardWidget(BaseWidget):
    """
    Widget to display Larry's messages.
    
    Options:
    - show_timestamp: bool (default True) - Show when message was sent
    - show_category: bool (default True) - Show message category icon
    - max_lines: int (default 8) - Maximum lines of text
    - font_size: int (default 24) - Base font size
    - title: str (default "Larry Says") - Widget title
    """

    name = "message_board"

    def render(self, draw: ImageDraw.ImageDraw, data: Dict[str, Any]) -> None:
        """Render the message board widget."""
        x, y = self.x, self.y
        width, height = self.width, self.height
        options = self.options

        # Options
        show_timestamp = options.get("show_timestamp", True)
        show_category = options.get("show_category", True)
        max_lines = options.get("max_lines", 8)
        font_size = options.get("font_size", 24)
        title = options.get("title", "🦔 Larry Says")

        # Fonts
        title_font = get_font(font_size + 8, bold=True)
        message_font = get_font(font_size)
        meta_font = get_font(font_size - 6)

        # Background
        draw.rectangle([x, y, x + width, y + height], fill="white", outline="black", width=2)

        # Title bar
        draw.rectangle([x, y, x + width, y + 45], fill="black")
        draw.text((x + 15, y + 8), title, font=title_font, fill="white")

        # Get message data
        msg_data = data.get("message_board", {})
        
        if not msg_data.get("available", False):
            # No messages available
            draw.text(
                (x + width // 2, y + height // 2),
                "No messages yet",
                font=message_font,
                fill="gray",
                anchor="mm",
            )
            return

        latest = msg_data.get("latest")
        
        if not latest:
            draw.text(
                (x + width // 2, y + height // 2),
                "No messages yet",
                font=message_font,
                fill="gray",
                anchor="mm",
            )
            return

        # Category icons
        category_icons = {
            "general": "💬",
            "workout": "🏃",
            "reminder": "⏰",
            "news": "📰",
            "weather": "🌤️",
            "motivation": "💪",
            "tip": "💡",
        }

        content_y = y + 55
        padding = 15

        # Category badge
        if show_category:
            category = latest.get("category", "general")
            icon = category_icons.get(category, "💬")
            draw.text((x + padding, content_y), icon, font=get_font(28))
            content_y += 40

        # Message text (wrapped)
        text = latest.get("text", "")
        char_width = font_size * 0.6
        wrap_width = int((width - padding * 2) / char_width)
        
        wrapped = textwrap.wrap(text, width=wrap_width)
        if len(wrapped) > max_lines:
            wrapped = wrapped[:max_lines]
            wrapped[-1] = wrapped[-1][:-3] + "..."

        for line in wrapped:
            draw.text((x + padding, content_y), line, font=message_font, fill="black")
            content_y += font_size + 6

        # Timestamp
        if show_timestamp:
            created = latest.get("created_at", "")
            if created:
                try:
                    dt_obj = dt.datetime.fromisoformat(created)
                    time_str = dt_obj.strftime("%I:%M %p · %b %d")
                    draw.text(
                        (x + padding, y + height - 30),
                        time_str,
                        font=meta_font,
                        fill="gray",
                    )
                except Exception:
                    pass

        # Priority indicator (high priority gets a marker)
        if latest.get("priority") == "high":
            draw.ellipse(
                [x + width - 25, y + 55, x + width - 10, y + 70],
                fill="black",
            )


@WidgetRegistry.register("message_board_compact")
class MessageBoardCompactWidget(BaseWidget):
    """Compact single-line message display."""

    name = "message_board_compact"

    def render(self, draw: ImageDraw.ImageDraw, data: Dict[str, Any]) -> None:
        """Render compact message."""
        x, y = self.x, self.y
        width, height = self.width, self.height
        
        font = get_font(self.options.get("font_size", 20))
        
        msg_data = data.get("message_board", {})
        latest = msg_data.get("latest")
        
        if latest:
            text = latest.get("text", "")
            # Truncate if too long
            max_chars = int(width / 12)
            if len(text) > max_chars:
                text = text[:max_chars - 3] + "..."
            
            icon = "🦔 "
            draw.text((x, y + (height - 24) // 2), icon + text, font=font, fill="black")
        else:
            draw.text((x, y + (height - 24) // 2), "🦔 ...", font=font, fill="gray")
