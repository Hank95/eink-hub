"""Configuration loading and validation for E-Ink Hub."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from .exceptions import ConfigurationError

_config: Optional["AppConfig"] = None


class ProviderConfig(BaseModel):
    """Configuration for a single data provider."""

    enabled: bool = True
    refresh_interval_minutes: int = 15
    credentials: Dict[str, str] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)


class WidgetConfig(BaseModel):
    """Configuration for a widget in a layout."""

    type: str
    x: int
    y: int
    width: int
    height: int
    provider: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class LayoutConfig(BaseModel):
    """Configuration for a display layout."""

    name: Optional[str] = None
    widgets: List[WidgetConfig] = Field(default_factory=list)
    background_color: int = 255  # 0=black, 255=white


class ScheduleConfig(BaseModel):
    """Scheduler configuration."""

    mode: str = "manual"  # "manual" | "auto_rotate"
    rotation_interval_minutes: int = 30
    layout_sequence: List[str] = Field(default_factory=list)
    quiet_hours: Optional[Dict[str, str]] = None  # {"start": "22:00", "end": "07:00"}

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid_modes = {"manual", "auto_rotate"}
        if v not in valid_modes:
            raise ValueError(f"mode must be one of {valid_modes}")
        return v


class DisplayConfig(BaseModel):
    """Display hardware configuration."""

    width: int = 800
    height: int = 480
    driver: str = "epd7in5_V2"
    mock_mode: bool = False


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: Optional[str] = None


class AppConfig(BaseModel):
    """Root configuration model."""

    display: DisplayConfig = Field(default_factory=DisplayConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    layouts: Dict[str, LayoutConfig] = Field(default_factory=dict)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def _substitute_env_vars(config_str: str) -> str:
    """
    Replace ${VAR} with environment variable values.

    Args:
        config_str: Raw config string with ${VAR} placeholders

    Returns:
        Config string with environment variables substituted

    Raises:
        ConfigurationError: If a referenced env var is not set
    """
    # Process line by line to skip comments
    lines = config_str.split('\n')
    result_lines = []

    pattern = r"\$\{(\w+)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            raise ConfigurationError(f"Missing environment variable: {var_name}")
        return value

    for line in lines:
        # Skip comment lines (allow leading whitespace)
        stripped = line.lstrip()
        if stripped.startswith('#'):
            result_lines.append(line)
        else:
            result_lines.append(re.sub(pattern, replacer, line))

    return '\n'.join(result_lines)


def load_config(path: Path = Path("config.yaml")) -> AppConfig:
    """
    Load and validate configuration from YAML file.

    Args:
        path: Path to config.yaml

    Returns:
        Validated AppConfig instance

    Raises:
        ConfigurationError: If config file is missing or invalid
    """
    global _config

    if not path.exists():
        raise ConfigurationError(f"Config file not found: {path}")

    try:
        raw_content = path.read_text()
        substituted = _substitute_env_vars(raw_content)
        data = yaml.safe_load(substituted)
        _config = AppConfig.model_validate(data or {})
        return _config
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in config file: {e}")
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(f"Failed to load config: {e}")


def get_config() -> AppConfig:
    """
    Get the current configuration (singleton pattern).

    Returns:
        Current AppConfig instance

    Raises:
        ConfigurationError: If config hasn't been loaded yet
    """
    global _config
    if _config is None:
        raise ConfigurationError("Configuration not loaded. Call load_config() first.")
    return _config


def reload_config(path: Path = Path("config.yaml")) -> AppConfig:
    """
    Hot-reload configuration from disk.

    Args:
        path: Path to config.yaml

    Returns:
        Newly loaded AppConfig instance
    """
    global _config
    _config = None
    return load_config(path)
