# eink_driver.py
from waveshare_epd import epd7in5_V2
from PIL import Image
from datetime import datetime
from pathlib import Path
from datetime import datetime
import json
from typing import Optional, Dict, Any

STATE_FILE = Path("state.json")


def _save_state(data: Dict[str, Any]) -> None:
    if STATE_FILE.exists():
        try:
            current = json.loads(STATE_FILE.read_text())
        except Exception:
            current = {}
    else:
        current = {}
    current.update(data)
    STATE_FILE.write_text(json.dumps(current, indent=2, default=str))


def get_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}

def send_to_display(image_path: Path, layout: str, options=None):
    print(f"[EINK] Updating display with {image_path}")

    epd = epd7in5_V2.EPD()
    epd.init()

    # Load your PNG and convert to 1-bit
    img = Image.open(image_path).convert("1")
    img = img.resize((epd.width, epd.height))

    epd.display(epd.getbuffer(img))
    epd.sleep()

    # Save state
    _save_state({
        "current_layout": layout,
        "current_image": str(image_path),
        "options": options or {},
        "last_updated": datetime.now().isoformat()
    })

    print("[EINK] Display updated.")
