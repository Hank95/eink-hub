"""Widget registration and discovery."""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from ..core.logging import get_logger
from .base import BaseWidget, WidgetBounds

logger = get_logger("widgets.registry")


class WidgetRegistry:
    """
    Registry for widget types.
    Uses decorator pattern for registration.
    """

    _widgets: Dict[str, Type[BaseWidget]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a widget class.

        Usage:
            @WidgetRegistry.register("clock")
            class ClockWidget(BaseWidget):
                ...
        """

        def decorator(widget_class: Type[BaseWidget]):
            cls._widgets[name] = widget_class
            widget_class.name = name
            logger.debug(f"Registered widget: {name}")
            return widget_class

        return decorator

    @classmethod
    def get_widget_class(cls, name: str) -> Optional[Type[BaseWidget]]:
        """Get a widget class by name."""
        return cls._widgets.get(name)

    @classmethod
    def create_widget(
        cls,
        widget_type: str,
        bounds: WidgetBounds,
        options: Optional[Dict] = None,
    ) -> BaseWidget:
        """
        Create a widget instance.

        Args:
            widget_type: Widget type name
            bounds: Widget position and size
            options: Widget-specific options

        Returns:
            Initialized widget instance

        Raises:
            ValueError: If widget type is unknown
        """
        widget_class = cls._widgets.get(widget_type)
        if not widget_class:
            raise ValueError(f"Unknown widget type: {widget_type}")
        return widget_class(bounds, options)

    @classmethod
    def list_registered(cls) -> List[str]:
        """List all registered widget types."""
        return list(cls._widgets.keys())
