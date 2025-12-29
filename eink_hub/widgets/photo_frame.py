"""Photo frame widget for displaying photos from uploads directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw

from ..core.image_processor import list_images, process_for_eink
from ..core.logging import get_logger
from ..core.state import StateManager
from .base import BaseWidget
from .registry import WidgetRegistry

logger = get_logger("widgets.photo_frame")

# Global reference to state manager (set during app init)
_state_manager: Optional[StateManager] = None


def set_state_manager(state_manager: StateManager) -> None:
    """Set the state manager for photo index tracking."""
    global _state_manager
    _state_manager = state_manager


@WidgetRegistry.register("photo_frame")
class PhotoFrameWidget(BaseWidget):
    """
    Photo frame widget that displays photos from the uploads directory.

    Cycles through available photos, showing the next one each time
    the widget is rendered (e.g., on each layout rotation).

    Options:
    - fit_mode: str (default: "fit") - "fit" (letterbox) or "fill" (crop)
    - rotation: int (default: 0) - Rotation angle (0, 90, 180, 270)
    - show_filename: bool (default: False) - Show filename at bottom
    - uploads_dir: str (default: "uploads") - Directory to scan for photos
    """

    name = "photo_frame"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render a photo from the uploads directory."""
        uploads_dir = Path(self.options.get("uploads_dir", "uploads"))
        fit_mode = self.options.get("fit_mode", "fit")
        rotation = self.options.get("rotation", 0)
        show_filename = self.options.get("show_filename", False)

        # Get list of photos
        photos = list_images(uploads_dir)

        if not photos:
            self._render_no_data(draw, "No photos in uploads/")
            return

        # Get current photo index from state
        photo_index = 0
        if _state_manager:
            state = _state_manager.get_state()
            photo_index = state.display.photo_index % len(photos)

            # Increment for next render
            next_index = (photo_index + 1) % len(photos)
            _state_manager.update_display_state(photo_index=next_index)

        # Get the photo to display
        photo_info = photos[photo_index]
        photo_path = photo_info["path"]

        try:
            # Process image for e-ink display
            processed = process_for_eink(
                photo_path,
                rotation=rotation,
                fit_mode=fit_mode,
                width=self.bounds.width,
                height=self.bounds.height,
            )

            # Convert to mode compatible with main canvas
            # The main canvas is likely "L" (grayscale), processed is "1" (1-bit)
            processed = processed.convert("L")

            # Access the underlying image from ImageDraw and paste
            canvas = draw._image
            canvas.paste(processed, (self.bounds.x, self.bounds.y))

            logger.info(f"Displayed photo: {photo_info['filename']} (index {photo_index})")

            # Optionally show filename
            if show_filename:
                font = self._load_font(12)
                filename = photo_info["filename"]
                text_y = self.bounds.y + self.bounds.height - 20
                draw.rectangle(
                    [self.bounds.x, text_y - 2,
                     self.bounds.x + self.bounds.width, self.bounds.y + self.bounds.height],
                    fill=255
                )
                draw.text(
                    (self.bounds.x + 5, text_y),
                    filename,
                    font=font,
                    fill=0
                )

        except Exception as e:
            logger.error(f"Failed to display photo {photo_path}: {e}")
            self._render_no_data(draw, f"Error: {str(e)[:30]}")

    def get_required_provider(self) -> Optional[str]:
        """Photo frame doesn't require a provider."""
        return None
