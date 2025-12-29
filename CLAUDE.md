# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

E-Ink Display Hub is a modular Python/FastAPI application for Raspberry Pi that controls a Waveshare 7.5" E-Ink display (V2, 800x480, B/W). It features a plugin-based architecture for data providers (Strava, Weather, Calendar, Indoor Sensor) and a widget-based layout system for composable displays.

## Running the Application

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pillow requests python-dotenv pyyaml httpx apscheduler icalendar pydantic

# Run server
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Architecture

```
eink_hub/
├── core/           # Infrastructure (config, logging, state, scheduler)
├── providers/      # Data sources (strava, weather, calendar, indoor_sensor)
├── widgets/        # Display components (clock, weather, calendar, etc.)
├── layouts/        # Layout rendering engine
├── display/        # E-ink driver wrapper
└── api/            # FastAPI routes
```

**Request flow:**
```
Web UI → FastAPI (api/routes.py) → LayoutRenderer → Widgets → DisplayDriver → Hardware
                                       ↑
                              Provider Data (cached)
```

**Key modules:**
- `eink_hub/core/config.py` - YAML config loading with `${ENV_VAR}` substitution
- `eink_hub/core/scheduler.py` - APScheduler for auto-refresh and rotation
- `eink_hub/providers/` - Plugin system with `@ProviderRegistry.register()` decorator
- `eink_hub/widgets/` - Widget system with `@WidgetRegistry.register()` decorator
- `eink_hub/layouts/renderer.py` - Composes widgets onto PIL canvas

## Configuration

All settings in `config.yaml`. Supports environment variable substitution:

```yaml
providers:
  strava:
    credentials:
      client_id: ${STRAVA_CLIENT_ID}
```

**Display modes:**
- `manual` - User triggers via web UI
- `auto_rotate` - Cycles through layouts automatically

## Adding New Providers

1. Create `eink_hub/providers/yourprovider.py`
2. Inherit from `BaseProvider`
3. Decorate with `@ProviderRegistry.register("yourprovider")`
4. Implement `_validate_config()` and `async fetch() -> ProviderData`
5. Add to `config.yaml` under `providers:`

## Adding New Widgets

1. Create `eink_hub/widgets/yourwidget.py`
2. Inherit from `BaseWidget`
3. Decorate with `@WidgetRegistry.register("yourwidget")`
4. Implement `render(draw, data)` method
5. Use in layouts via `type: yourwidget`

## Environment Variables

Required in `.env`:
```
STRAVA_CLIENT_ID=...
STRAVA_CLIENT_SECRET=...
STRAVA_REFRESH_TOKEN=...
OPENWEATHER_API_KEY=...
CALENDAR_ICAL_URL=...
```

## Hardware Constraints

- E-ink displays have slow refresh (~2-3 seconds)
- Display resolution: 800x480 pixels
- SPI requires root or GPIO permissions
- Set `display.mock_mode: true` in config for development without hardware
