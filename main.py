# main.py
"""E-Ink Hub - Desktop information display for Raspberry Pi."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables before importing config
load_dotenv()

from eink_hub.core.config import load_config, get_config, set_config
from eink_hub.core.image_processor import list_images, process_for_eink
from eink_hub.core.logging import setup_logging, get_logger
from eink_hub.core.scheduler import HubScheduler
from eink_hub.core.state import StateManager
from eink_hub.providers.registry import ProviderRegistry
from eink_hub.layouts.renderer import LayoutRenderer
from eink_hub.display.driver import DisplayDriver
from eink_hub.api.routes import router as api_router, init_routes
from eink_hub.widgets.photo_frame import set_state_manager as set_photo_state_manager

# Import providers to trigger registration
from eink_hub.providers import strava, weather, calendar, todoist, indoor_sensor  # noqa: F401

logger = get_logger("main")

# Global instances
state_manager = StateManager()
scheduler = HubScheduler()
renderer: LayoutRenderer = None
display_driver: DisplayDriver = None


async def _refresh_provider(provider_name: str) -> None:
    """Refresh a single provider's data."""
    provider = ProviderRegistry.get_instance(provider_name)
    if provider:
        try:
            data = await provider.fetch()
            state_manager.update_provider_state(provider_name, data.data)
            logger.debug(f"Provider refreshed: {provider_name}")
        except Exception as e:
            logger.error(f"Provider refresh failed: {provider_name} - {e}")
            state_manager.update_provider_state(provider_name, {}, error=str(e))


async def _rotate_display() -> None:
    """Rotate to the next layout in the sequence."""
    config = get_config()
    state = state_manager.get_state()

    sequence = config.schedule.layout_sequence
    if not sequence:
        logger.warning("No layouts in rotation sequence")
        return

    # Get next layout
    current_index = state.display.rotation_index
    next_index = (current_index + 1) % len(sequence)
    next_layout = sequence[next_index]

    # Update state
    state_manager.update_display_state(rotation_index=next_index)

    # Render and display
    provider_data = state_manager.get_all_provider_data()
    image_path = renderer.render_layout(next_layout, provider_data)
    display_driver.send_to_display(image_path, next_layout)

    logger.info(f"Rotated to layout: {next_layout}")


async def _rotate_photos() -> None:
    """Rotate to the next photo in slideshow mode."""
    config = get_config()
    state = state_manager.get_state()

    # Get list of photos
    photos = list_images(Path("uploads"))
    if not photos:
        logger.warning("No photos in uploads/ for slideshow")
        return

    # Get current photo index
    current_index = state.display.photo_index
    next_index = (current_index + 1) % len(photos)

    # Update state
    state_manager.update_display_state(photo_index=next_index)

    # Process and display the photo
    photo_path = photos[next_index]["path"]

    try:
        processed = process_for_eink(
            photo_path,
            rotation=config.schedule.photo_rotation,
            fit_mode=config.schedule.photo_fit_mode,
        )

        # Save to preview
        output_path = Path("previews") / "photo_slideshow.png"
        output_path.parent.mkdir(exist_ok=True)
        processed.save(output_path)

        # Send to display
        display_driver.send_to_display(output_path, "photo_slideshow")

        logger.info(f"Photo slideshow: {photos[next_index]['filename']} (index {next_index})")

    except Exception as e:
        logger.error(f"Failed to display photo {photo_path}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global renderer, display_driver

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        # Create minimal config for startup and set it globally
        from eink_hub.core.config import AppConfig
        config = AppConfig()
        set_config(config)

    # Setup logging
    log_config = config.logging
    setup_logging(
        level=log_config.level,
        log_file=Path(log_config.file) if log_config.file else None,
    )

    logger.info("E-Ink Hub starting...")

    # Initialize components
    renderer = LayoutRenderer(
        width=config.display.width,
        height=config.display.height,
    )
    display_driver = DisplayDriver(
        state_manager=state_manager,
        mock_mode=config.display.mock_mode,
    )

    # Set state manager for photo frame widget
    set_photo_state_manager(state_manager)

    # Initialize API routes with rotation callbacks
    init_routes(
        state_manager,
        scheduler,
        renderer,
        display_driver,
        rotate_display_callback=_rotate_display,
        rotate_photos_callback=_rotate_photos,
    )

    # Initialize enabled providers
    for name, prov_config in config.providers.items():
        if prov_config.enabled:
            try:
                ProviderRegistry.create_provider(name, prov_config.model_dump())
                logger.info(f"Initialized provider: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {name}: {e}")

    # Start scheduler
    await scheduler.start()

    # Schedule provider refreshes
    for name, prov_config in config.providers.items():
        if prov_config.enabled:
            scheduler.schedule_provider_refresh(
                name,
                lambda n=name: _refresh_provider(n),
                prov_config.refresh_interval_minutes,
            )

    # Initial provider refresh
    for name, prov_config in config.providers.items():
        if prov_config.enabled:
            try:
                await _refresh_provider(name)
            except Exception as e:
                logger.warning(f"Initial refresh failed for {name}: {e}")

    # Set display mode from state or config
    state = state_manager.get_state()
    if state.display.mode == "auto_rotate":
        scheduler.schedule_display_rotation(
            _rotate_display,
            config.schedule.rotation_interval_minutes,
        )
    elif state.display.mode == "photo_slideshow":
        scheduler.schedule_display_rotation(
            _rotate_photos,
            config.schedule.photo_interval_minutes,
        )

    # Set quiet hours if configured
    if config.schedule.quiet_hours:
        scheduler.set_quiet_hours(
            config.schedule.quiet_hours.get("start", "22:00"),
            config.schedule.quiet_hours.get("end", "07:00"),
        )

    logger.info("E-Ink Hub ready")

    yield

    # Shutdown
    await scheduler.stop()
    logger.info("E-Ink Hub stopped")


app = FastAPI(title="E-Ink Hub", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the web dashboard."""
    return Path("static/index.html").read_text()


@app.get("/sensors", response_class=HTMLResponse)
async def sensors_page():
    """Serve the sensor history page."""
    return Path("static/sensors.html").read_text()


@app.get("/strava", response_class=HTMLResponse)
async def strava_page():
    """Serve the Strava history page."""
    return Path("static/strava.html").read_text()
