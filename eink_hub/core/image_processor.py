"""Image processing utilities for e-ink display."""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional, Tuple

from PIL import Image

from .logging import get_logger

logger = get_logger("core.image_processor")

# Display constants
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

FitMode = Literal["fit", "fill"]


def process_for_eink(
    image_path: str | Path,
    rotation: int = 0,
    fit_mode: FitMode = "fit",
    width: int = DISPLAY_WIDTH,
    height: int = DISPLAY_HEIGHT,
) -> Image.Image:
    """
    Process an image for e-ink display.

    Args:
        image_path: Path to the source image
        rotation: Rotation angle (0, 90, 180, 270)
        fit_mode: 'fit' (letterbox with white padding) or 'fill' (crop to fill)
        width: Target width in pixels
        height: Target height in pixels

    Returns:
        Processed PIL Image in 1-bit mode (black/white)
    """
    logger.debug(f"Processing image: {image_path}, rotation={rotation}, fit_mode={fit_mode}")

    # Load image
    img = Image.open(image_path)

    # Convert to RGB if necessary (handles RGBA, palette, etc.)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Apply rotation
    if rotation in (90, 180, 270):
        # PIL rotates counter-clockwise, so we negate for clockwise rotation
        img = img.rotate(-rotation, expand=True)

    # Get current dimensions after rotation
    img_width, img_height = img.size

    # Calculate scaling based on fit mode
    if fit_mode == "fit":
        # Scale to fit within bounds, maintaining aspect ratio
        scale = min(width / img_width, height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        # Resize with high-quality resampling
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create white canvas and paste centered
        canvas = Image.new("RGB", (width, height), (255, 255, 255))
        x_offset = (width - new_width) // 2
        y_offset = (height - new_height) // 2
        canvas.paste(img, (x_offset, y_offset))
        img = canvas

    else:  # fill mode - crop to fill
        # Scale to fill bounds, maintaining aspect ratio
        scale = max(width / img_width, height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        # Resize with high-quality resampling
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Crop from center
        x_offset = (new_width - width) // 2
        y_offset = (new_height - height) // 2
        img = img.crop((x_offset, y_offset, x_offset + width, y_offset + height))

    # Convert to grayscale
    img = img.convert("L")

    # Convert to 1-bit with Floyd-Steinberg dithering for better appearance
    img = img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)

    return img


def generate_preview(
    image_path: str | Path,
    rotation: int = 0,
    fit_mode: FitMode = "fit",
) -> bytes:
    """
    Generate a monochrome preview image as PNG bytes.

    Args:
        image_path: Path to the source image
        rotation: Rotation angle (0, 90, 180, 270)
        fit_mode: 'fit' or 'fill'

    Returns:
        PNG image as bytes
    """
    img = process_for_eink(image_path, rotation, fit_mode)

    # Convert to grayscale for preview (easier to see than pure 1-bit)
    # This simulates what the e-ink display will look like
    preview = img.convert("L")

    # Save to bytes
    buffer = BytesIO()
    preview.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()


def save_processed_image(
    image_path: str | Path,
    output_path: str | Path,
    rotation: int = 0,
    fit_mode: FitMode = "fit",
) -> Path:
    """
    Process an image and save it to disk.

    Args:
        image_path: Path to the source image
        output_path: Path to save the processed image
        rotation: Rotation angle (0, 90, 180, 270)
        fit_mode: 'fit' or 'fill'

    Returns:
        Path to the saved image
    """
    img = process_for_eink(image_path, rotation, fit_mode)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img.save(output_path, format="PNG")
    logger.info(f"Saved processed image to {output_path}")

    return output_path


def get_image_metadata(image_path: str | Path) -> dict:
    """
    Get metadata for an image file.

    Args:
        image_path: Path to the image

    Returns:
        Dictionary with filename, size_bytes, width, height, uploaded_at
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    # Get file stats
    stat = path.stat()
    size_bytes = stat.st_size
    uploaded_at = datetime.fromtimestamp(stat.st_mtime)

    # Get image dimensions
    try:
        with Image.open(path) as img:
            width, height = img.size
    except Exception as e:
        logger.warning(f"Could not read image dimensions for {path}: {e}")
        width, height = 0, 0

    return {
        "filename": path.name,
        "path": str(path),
        "size_bytes": size_bytes,
        "width": width,
        "height": height,
        "uploaded_at": uploaded_at.isoformat(),
    }


def list_images(directory: str | Path) -> list[dict]:
    """
    List all images in a directory with metadata.

    Args:
        directory: Path to the directory

    Returns:
        List of image metadata dictionaries, sorted by upload time (newest first)
    """
    directory = Path(directory)

    if not directory.exists():
        return []

    # Supported image extensions
    extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

    images = []
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            try:
                metadata = get_image_metadata(file_path)
                images.append(metadata)
            except Exception as e:
                logger.warning(f"Could not read image {file_path}: {e}")

    # Sort by upload time, newest first
    images.sort(key=lambda x: x["uploaded_at"], reverse=True)

    return images


def generate_thumbnail(
    image_path: str | Path,
    max_size: Tuple[int, int] = (150, 150),
) -> bytes:
    """
    Generate a thumbnail for an image.

    Args:
        image_path: Path to the source image
        max_size: Maximum thumbnail dimensions

    Returns:
        JPEG thumbnail as bytes
    """
    with Image.open(image_path) as img:
        # Convert to RGB for JPEG
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Create thumbnail (modifies in place)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save to bytes
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        return buffer.getvalue()
