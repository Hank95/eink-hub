"""Custom exception hierarchy for E-Ink Hub."""


class EinkHubError(Exception):
    """Base exception for all eink-hub errors."""

    pass


class ConfigurationError(EinkHubError):
    """Invalid or missing configuration."""

    pass


class ProviderError(EinkHubError):
    """Error fetching data from a provider."""

    def __init__(
        self, provider_name: str, message: str, recoverable: bool = True
    ) -> None:
        self.provider_name = provider_name
        self.recoverable = recoverable
        super().__init__(f"[{provider_name}] {message}")


class DisplayError(EinkHubError):
    """Error communicating with display hardware."""

    pass


class WidgetRenderError(EinkHubError):
    """Error rendering a widget."""

    def __init__(self, widget_type: str, message: str) -> None:
        self.widget_type = widget_type
        super().__init__(f"Widget '{widget_type}': {message}")
