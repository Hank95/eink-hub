"""Abstract base class for data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from ..core.exceptions import ConfigurationError


class ProviderData(BaseModel):
    """Standard wrapper for provider output."""

    provider_name: str
    fetched_at: datetime
    data: Dict[str, Any]
    ttl_seconds: int = 900  # How long this data is valid (15 min default)


class BaseProvider(ABC):
    """
    Abstract base class for all data providers.

    Each provider:
    - Has a unique name
    - Fetches data from an external source
    - Returns standardized ProviderData
    - Handles its own errors gracefully
    """

    name: str  # Unique identifier, e.g., "weather", "strava"

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize with provider-specific configuration.

        Args:
            config: Contains 'credentials' and 'options' from YAML
        """
        self.config = config
        self.credentials = config.get("credentials", {})
        self.options = config.get("options", {})
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """
        Validate required configuration is present.

        Raises:
            ConfigurationError: If required config is missing
        """
        pass

    @abstractmethod
    async def fetch(self) -> ProviderData:
        """
        Fetch fresh data from the source.

        Returns:
            ProviderData with the fetched information

        Raises:
            ProviderError: If fetch fails
        """
        pass

    def get_default_refresh_interval(self) -> int:
        """
        Return default refresh interval in minutes.

        Returns:
            Refresh interval in minutes
        """
        return 15

    def health_check(self) -> bool:
        """
        Check if provider credentials/config are valid.

        Returns:
            True if provider is properly configured
        """
        try:
            self._validate_config()
            return True
        except ConfigurationError:
            return False

    def _require_credential(self, key: str) -> str:
        """
        Get a required credential, raising if missing.

        Args:
            key: Credential key name

        Returns:
            Credential value

        Raises:
            ConfigurationError: If credential is missing
        """
        value = self.credentials.get(key)
        if not value:
            raise ConfigurationError(
                f"{self.name} provider requires credential: {key}"
            )
        return value

    def _require_option(self, key: str) -> Any:
        """
        Get a required option, raising if missing.

        Args:
            key: Option key name

        Returns:
            Option value

        Raises:
            ConfigurationError: If option is missing
        """
        value = self.options.get(key)
        if value is None:
            raise ConfigurationError(
                f"{self.name} provider requires option: {key}"
            )
        return value
