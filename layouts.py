# layouts.py
from pathlib import Path
from typing import Literal, Optional, Dict, Any
from datetime import datetime
from strava_client import get_week_summary

from PIL import Image, ImageDraw, ImageFont

# Adjust to your e-ink resolution
EINK_WIDTH = 800
EINK_HEIGHT = 480

LayoutType = Literal["daily_rundown", "photo_frame", "strava_dashboard"]

PREVIEW_DIR = Path("previews")
PREVIEW_DIR.mkdir(exist_ok=True)


def _base_image() -> Image.Image:
    """Create a blank white canvas."""
    img = Image.new("L", (EINK_WIDTH, EINK_HEIGHT), color=255)  # L = 8-bit grayscale
    return img


def _load_font(size: int = 24) -> ImageFont.FreeTypeFont:
    # Try a couple of common font paths; fall back to default
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    """
    Compatibility helper: Pillow 10+ removed textsize, use textbbox instead.
    Returns (width, height).
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height

def render_daily_rundown(options: Optional[Dict[str, Any]] = None) -> Path:
    """
    Very simple daily rundown layout:
    - Date + time
    - Placeholder for 'today's run'
    - Placeholder for 'today's events'
    """
    options = options or {}

    img = _base_image()
    draw = ImageDraw.Draw(img)

    title_font = _load_font(32)
    body_font = _load_font(20)

    now = datetime.now()
    date_str = now.strftime("%A, %B %d")
    time_str = now.strftime("%I:%M %p")

    # Header
    draw.text((30, 20), "Daily Rundown", font=title_font, fill=0)
    draw.text((30, 70), date_str, font=body_font, fill=0)
    draw.text((30, 100), time_str, font=body_font, fill=0)

    # Left block: run
    y_run = 150
    draw.text((30, y_run), "Today's Run", font=body_font, fill=0)
    run_text = options.get("run_text", "8 mi base · easy pace")
    draw.text((30, y_run + 30), f"Plan: {run_text}", font=body_font, fill=0)

    # Right block: events (for now, stub)
    y_events = 150
    x_events = 420
    draw.text((x_events, y_events), "Today's Events", font=body_font, fill=0)
    events = options.get(
        "events",
        [
            "10:30 – CB Insights call",
            "1:00 – Work block",
            "6:30 – Dinner",
        ],
    )
    y = y_events + 30
    for ev in events[:6]:
        draw.text((x_events, y), f"- {ev}", font=body_font, fill=0)
        y += 24

    # Footer
    footer = "hp95 · e-ink hub"
    w, _ = _text_size(draw, footer, body_font)
    draw.text((EINK_WIDTH - w - 20, EINK_HEIGHT - 40), footer, font=body_font, fill=0)
    out_path = PREVIEW_DIR / "daily_rundown.png"
    img.save(out_path)
    return out_path


def render_photo_frame(options: Optional[Dict[str, Any]] = None) -> Path:
    """Render a photo with optional caption."""
    options = options or {}
    photo_path = options.get("photo_path")
    caption = options.get("caption", "")

    img = _base_image()
    draw = ImageDraw.Draw(img)
    body_font = _load_font(20)
    title_font = _load_font(28)

    if photo_path and Path(photo_path).exists():
        photo = Image.open(photo_path).convert("L")
        # Fit photo into a rectangle with some margins
        margin = 40
        caption_space = 80
        target_w = EINK_WIDTH - margin * 2
        target_h = EINK_HEIGHT - margin * 2 - caption_space

        photo.thumbnail((target_w, target_h))
        pw, ph = photo.size
        x = (EINK_WIDTH - pw) // 2
        y = margin
        img.paste(photo, (x, y))
    else:
        # Fallback: just a message
        msg = "No photo selected"
        w, h = _text_size(draw, msg, title_font)
        draw.text(
            ((EINK_WIDTH - w) // 2, (EINK_HEIGHT - h) // 2),
            msg,
            font=title_font,
            fill=0,
        )

    # Draw caption strip
    if caption:
        draw.rectangle(
            [0, EINK_HEIGHT - 80, EINK_WIDTH, EINK_HEIGHT], fill=255, outline=0
        )
        w, _ = draw.textsize(caption, font=body_font)
        draw.text(
            ((EINK_WIDTH - w) // 2, EINK_HEIGHT - 60),
            caption,
            font=body_font,
            fill=0,
        )

    out_path = PREVIEW_DIR / "photo_frame.png"
    img.save(out_path)
    return out_path

def render_strava_dashboard(options: dict) -> Path:
    WIDTH, HEIGHT = 800, 480
    img = Image.new("1", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40
        )
        subtitle_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26
        )
        body_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22
        )
        small_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18
        )
    except Exception:
        title_font = subtitle_font = body_font = small_font = ImageFont.load_default()

    # ----------------- Fetch Strava data -----------------
    summary = get_week_summary()

    weekly_miles = summary.get("weekly_miles")
    if not weekly_miles or not isinstance(weekly_miles, list):
        weekly_miles = [6.2, 8.1, 5.0, 0.0, 7.3, 10.5, 4.2]

    week_total = summary.get("week_total_miles")
    if not isinstance(week_total, (int, float)):
        week_total = round(sum(weekly_miles), 1)

    recent_runs = summary.get("recent_runs")
    if not recent_runs or not isinstance(recent_runs, list):
        recent_runs = [
            {"label": "Sat Long Run", "miles": 18.2, "pace": "8:05 /mi"},
            {"label": "Thu Tempo", "miles": 7.5, "pace": "7:20 /mi"},
            {"label": "Tue Easy", "miles": 6.0, "pace": "8:40 /mi"},
        ]

    # ----------------- Header -----------------
    title = "Strava Weekly"
    tb = draw.textbbox((0, 0), title, font=title_font)
    tw = tb[2] - tb[0]
    draw.text(((WIDTH - tw) // 2, 18), title, font=title_font, fill=0)

    subtitle = f"This week: {week_total:.1f} mi"
    sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    sw = sb[2] - sb[0]
    draw.text(((WIDTH - sw) // 2, 70), subtitle, font=subtitle_font, fill=0)

    # Draw a subtle divider under the header
    draw.line((40, 110, WIDTH - 40, 110), fill=0, width=1)

    # Split screen into left (recent runs) and right (chart)
    split_x = WIDTH // 2

    # ----------------- Recent runs (left side) -----------------
    left_margin = 40
    y = 130

    rr_title = "Recent runs"
    rrtb = draw.textbbox((0, 0), rr_title, font=body_font)
    draw.text((left_margin, y), rr_title, font=body_font, fill=0)
    y += (rrtb[3] - rrtb[1]) + 10

    # Show up to 4 recent runs
    for run in recent_runs[:4]:
        label = str(run.get("label", "Run"))
        miles = float(run.get("miles", 0.0) or 0.0)
        pace = str(run.get("pace", ""))

        # Line 1: name
        draw.text((left_margin, y), label, font=body_font, fill=0)
        y += 22

        # Line 2: distance + pace
        details = f"{miles:.1f} mi  •  {pace}"
        draw.text((left_margin, y), details, font=small_font, fill=0)
        y += 30  # spacing before next entry

    # ----------------- Weekly bar chart (right side) -----------------
    chart_left = split_x + 30
    chart_right = WIDTH - 40
    chart_top = 130
    chart_bottom = HEIGHT - 60

    # Box for the chart
    draw.rectangle(
        (chart_left, chart_top, chart_right, chart_bottom),
        outline=0,
        width=1,
    )

    days = ["M", "T", "W", "T", "F", "S", "S"]
    num_days = min(7, len(weekly_miles))
    max_miles = max(weekly_miles) if weekly_miles else 1.0
    if max_miles <= 0:
        max_miles = 1.0

    bar_area_height = chart_bottom - chart_top - 35  # leave room for labels
    bar_area_width = chart_right - chart_left

    for i in range(num_days):
        m = float(weekly_miles[i] or 0.0)
        frac = m / max_miles
        bar_h = frac * bar_area_height

        x_center = chart_left + (i + 0.5) * (bar_area_width / num_days)
        bar_w = bar_area_width / (num_days * 1.6)

        x0 = int(x_center - bar_w / 2)
        x1 = int(x_center + bar_w / 2)
        y1 = chart_bottom - 20
        y0 = int(y1 - bar_h)

        # Bar
        if m > 0:
            draw.rectangle((x0, y0, x1, y1), fill=0, outline=0)

        # Day label under bar
        day_label = days[i]
        db = draw.textbbox((0, 0), day_label, font=small_font)
        dw = db[2] - db[0]
        draw.text((int(x_center - dw / 2), chart_bottom - 18), day_label, font=small_font, fill=0)

    # Optional: small max label in top-right of chart
    max_label = f"Max: {max_miles:.1f} mi"
    mlb = draw.textbbox((0, 0), max_label, font=small_font)
    mlw = mlb[2] - mlb[0]
    draw.text((chart_right - mlw - 4, chart_top + 4), max_label, font=small_font, fill=0)

    out_path = PREVIEW_DIR / "strava_dashboard.png"
    img.save(out_path)
    return out_path

def render_layout(layout: str, options: dict) -> Path:
    if layout == "daily_rundown":
        return render_daily_rundown(options)
    elif layout == "photo_frame":
        return render_photo_frame(options)
    elif layout == "strava_dashboard":
        return render_strava_dashboard(options)
    else:
        raise ValueError(f"Unknown layout: {layout}")
