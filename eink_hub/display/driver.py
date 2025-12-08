"""E-Ink display driver wrapper."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

from ..core.config import get_config
from ..core.exceptions import DisplayError
from ..core.logging import get_logger
from ..core.state import StateManager

logger = get_logger("display.driver")


class DisplayDriver:
    """
    E-Ink display driver wrapper.

    Handles communication with the Waveshare e-ink display,
    with mock mode support for development.
    """

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        self._state_manager = state_manager or StateManager()
        self._epd = None

        # Determine mock mode
        if mock_mode is not None:
            self._mock_mode = mock_mode
        else:
            try:
                config = get_config()
                self._mock_mode = config.display.mock_mode
            except Exception:
                self._mock_mode = True  # Default to mock if no config

    def _init_display(self) -> None:
        """Initialize the e-ink display hardware."""
        if self._mock_mode:
            logger.info("Display in mock mode - skipping hardware init")
            return

        try:
            from waveshare_epd import epd7in5_V2

            if self._epd is None:
                self._epd = epd7in5_V2.EPD()
                logger.info("E-ink display created")

            # Always call init() to wake the display from sleep
            self._epd.init()
            logger.info("E-ink display initialized")
        except ImportError:
            logger.warning("Waveshare EPD library not available, using mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            raise DisplayError(f"Display initialization failed: {e}")

    def send_to_display(
        self,
        image_path: Path,
        layout: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Send an image to the e-ink display.

        Args:
            image_path: Path to the PNG image
            layout: Name of the layout being displayed
            options: Optional layout options
        """
        logger.info(f"Updating display with {image_path}")

        if not self._mock_mode:
            self._init_display()

            try:
                # Load and convert image
                img = Image.open(image_path).convert("1")  # 1-bit black/white
                img = img.resize((self._epd.width, self._epd.height))

                # Send to display
                self._epd.display(self._epd.getbuffer(img))
                self._epd.sleep()

                logger.info("Display updated successfully")
            except Exception as e:
                logger.error(f"Display update failed: {e}")
                raise DisplayError(f"Failed to update display: {e}")
        else:
            logger.info("Mock mode: would update display")

        # Save state
        self._state_manager.update_display_state(
            current_layout=layout,
            current_image=str(image_path),
            last_updated=datetime.now(),
        )

    def clear_display(self) -> None:
        """Clear the display to white."""
        logger.info("Clearing display")

        if not self._mock_mode:
            self._init_display()

            try:
                self._epd.Clear()
                self._epd.sleep()
                logger.info("Display cleared")
            except Exception as e:
                logger.error(f"Display clear failed: {e}")
                raise DisplayError(f"Failed to clear display: {e}")
        else:
            logger.info("Mock mode: would clear display")

    def sleep_display(self) -> None:
        """Put the display into sleep mode."""
        if not self._mock_mode and self._epd:
            try:
                self._epd.sleep()
                logger.debug("Display put to sleep")
            except Exception as e:
                logger.warning(f"Failed to sleep display: {e}")
