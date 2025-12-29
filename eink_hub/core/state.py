"""State persistence and management for E-Ink Hub."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .logging import get_logger

logger = get_logger("core.state")


class DisplayState(BaseModel):
    """Current display state."""

    current_layout: Optional[str] = None
    current_image: Optional[str] = None
    last_updated: Optional[datetime] = None
    mode: str = "manual"  # "manual" | "auto_rotate" | "photo_slideshow"
    rotation_index: int = 0
    photo_index: int = 0  # Tracks position in photo rotation


class ProviderState(BaseModel):
    """Cached data from a provider."""

    last_fetch: Optional[datetime] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class AppState(BaseModel):
    """Complete application state."""

    display: DisplayState = Field(default_factory=DisplayState)
    providers: Dict[str, ProviderState] = Field(default_factory=dict)


class StateManager:
    """Thread-safe state persistence manager."""

    def __init__(self, state_file: Path = Path("state.json")) -> None:
        self._state_file = state_file
        self._state: Optional[AppState] = None

    def _load(self) -> AppState:
        """Load state from disk."""
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())
                return AppState.model_validate(data)
            except Exception as e:
                logger.warning(f"Failed to load state file, using defaults: {e}")
        return AppState()

    def _save(self) -> None:
        """Save state to disk."""
        if self._state is None:
            return
        try:
            self._state_file.write_text(
                self._state.model_dump_json(indent=2, exclude_none=False)
            )
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get_state(self) -> AppState:
        """Get current state, loading from disk if needed."""
        if self._state is None:
            self._state = self._load()
        return self._state

    def update_display_state(self, **kwargs: Any) -> None:
        """
        Update display state fields.

        Args:
            **kwargs: Fields to update (current_layout, current_image, mode, etc.)
        """
        state = self.get_state()
        for key, value in kwargs.items():
            if hasattr(state.display, key):
                setattr(state.display, key, value)
        self._save()
        logger.debug(f"Display state updated: {kwargs}")

    def update_provider_state(
        self,
        provider_name: str,
        data: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        """
        Update cached provider data.

        Args:
            provider_name: Name of the provider
            data: Provider data to cache
            error: Error message if fetch failed
        """
        state = self.get_state()
        state.providers[provider_name] = ProviderState(
            last_fetch=datetime.now(),
            data=data,
            error=error,
        )
        self._save()
        if error:
            logger.warning(f"Provider {provider_name} error cached: {error}")
        else:
            logger.debug(f"Provider {provider_name} data cached")

    def get_provider_data(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Cached data dict or None if not available
        """
        state = self.get_state()
        provider_state = state.providers.get(provider_name)
        if provider_state and provider_state.data:
            return provider_state.data
        return None

    def get_all_provider_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cached provider data.

        Returns:
            Dict mapping provider names to their cached data
        """
        state = self.get_state()
        return {
            name: prov.data
            for name, prov in state.providers.items()
            if prov.data
        }

    def clear_provider_data(self, provider_name: str) -> None:
        """Clear cached data for a provider."""
        state = self.get_state()
        if provider_name in state.providers:
            del state.providers[provider_name]
            self._save()
            logger.debug(f"Cleared provider data: {provider_name}")
