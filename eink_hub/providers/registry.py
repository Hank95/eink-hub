"""Provider registration and discovery."""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from ..core.exceptions import ConfigurationError
from ..core.logging import get_logger
from .base import BaseProvider

logger = get_logger("providers.registry")


class ProviderRegistry:
    """
    Registry for discovering and instantiating providers.
    Uses decorator pattern for registration.
    """

    _providers: Dict[str, Type[BaseProvider]] = {}
    _instances: Dict[str, BaseProvider] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a provider class.

        Usage:
            @ProviderRegistry.register("weather")
            class WeatherProvider(BaseProvider):
                ...
        """

        def decorator(provider_class: Type[BaseProvider]):
            cls._providers[name] = provider_class
            provider_class.name = name
            logger.debug(f"Registered provider: {name}")
            return provider_class

        return decorator

    @classmethod
    def get_provider_class(cls, name: str) -> Optional[Type[BaseProvider]]:
        """Get a provider class by name."""
        return cls._providers.get(name)

    @classmethod
    def create_provider(cls, name: str, config: Dict) -> BaseProvider:
        """
        Instantiate a provider with configuration.

        Args:
            name: Provider type name
            config: Provider configuration dict

        Returns:
            Initialized provider instance

        Raises:
            ConfigurationError: If provider type is unknown
        """
        provider_class = cls._providers.get(name)
        if not provider_class:
            raise ConfigurationError(f"Unknown provider type: {name}")

        instance = provider_class(config)
        cls._instances[name] = instance
        logger.info(f"Created provider instance: {name}")
        return instance

    @classmethod
    def get_instance(cls, name: str) -> Optional[BaseProvider]:
        """Get an already-instantiated provider."""
        return cls._instances.get(name)

    @classmethod
    def list_registered(cls) -> List[str]:
        """List all registered provider types."""
        return list(cls._providers.keys())

    @classmethod
    def list_instances(cls) -> List[str]:
        """List all instantiated providers."""
        return list(cls._instances.keys())

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all provider instances (useful for testing)."""
        cls._instances.clear()
