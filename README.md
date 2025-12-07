
# 📘 E-Ink Display Hub

A Raspberry Pi–powered E-Ink dashboard that can display:

- **Daily Rundown** (calendar, upcoming run, summary)
- **Photo Frame Mode** (upload an image + caption)
- **Strava Weekly Dashboard** (weekly mileage, run summaries, bar chart)

Runs on a Waveshare **7.5-inch E-Ink V2** display with an SPI driver HAT.
Includes a FastAPI backend, web control panel, and optional Strava integration.

---

## ✨ Features

### 🗓 Daily Rundown
A clean daily schedule or summary image rendered via Python + PIL.

### 🖼 Photo Frame Mode
Upload a photo from the dashboard — instantly displayed on the panel.

### 🏃 Strava Dashboard
Pulls activity data using the Strava API and shows:

- Weekly total mileage
- Bar chart of the past 7 days
- Recent run list (distance, pace, date)

Perfect for runners and daily training visualization.

---

## 🛠 Hardware Required

- Raspberry Pi 3 / 4 / 5
- Waveshare 7.5" E-Paper Display V2 (B/W)
- Waveshare E-Paper Driver HAT (SPI)
- 8-pin ribbon cable
- MicroSD card
- Power supply

---

## 🪛 Hardware Setup (SPI)

1. Attach the **E-Paper Driver HAT** to the Pi GPIO header.
2. Connect the 8-pin cable to the HAT’s **DISPLAY** connector and the screen.
3. Set the interface switch to **4-line SPI**.
4. Enable SPI:

```bash
sudo raspi-config
# Interface Options → SPI → Enable
sudo reboot
```

---

## 🧰 Software Installation

Clone the repo:

```bash
git clone https://github.com/yourname/eink-hub.git
cd eink-hub
```

Create & activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start the server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open the dashboard:

```
http://<raspberry-pi-ip>:8000
```

---

## 🔐 Environment Variables (`.env`)

Create a `.env` file:

```
STRAVA_CLIENT_ID=xxxx
STRAVA_CLIENT_SECRET=yyyy
STRAVA_REFRESH_TOKEN=zzzz
```

This file stays private and is ignored by Git.

---

## 🏃 Strava Integration

The `strava_client.py` module:

- Automatically exchanges refresh tokens
- Downloads your recent activities
- Computes weekly mileage
- Formats data for the Strava dashboard layout

Test it manually:

```bash
python3 strava_client.py
```

---

## 🌐 API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/status` | GET | Returns current layout + last update |
| `/api/display` | POST | Renders & sends a layout to the display |
| `/api/upload` | POST | Upload a photo for Photo Frame mode |
| `/api/preview` | GET | Returns the last preview image |

---

## 🗂 Project Structure

```
eink-hub/
│
├── main.py                 # FastAPI server
├── layouts.py              # Layout rendering functions
├── eink_driver.py          # Low-level Waveshare driver wrapper
├── strava_client.py        # Strava API integration
│
├── static/                 # Dashboard UI (HTML/CSS/JS)
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── previews/               # Generated preview images (gitignored)
├── uploads/                # Uploaded photos (gitignored)
│
├── waveshare_epd/          # Vendor driver code
├── .env                    # API secrets (gitignored)
└── README.md
```

---

## 🚀 Optional: Run on Boot with systemd

Create the service:

```bash
sudo nano /etc/systemd/system/eink-hub.service
```

Paste:

```
[Unit]
Description=E-Ink Hub Service
After=network.target

[Service]
WorkingDirectory=/home/pi/eink-hub
ExecStart=/home/pi/eink-hub/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl enable eink-hub
sudo systemctl start eink-hub
```

---

## 📜 License

MIT License — build your own dashboard and customize freely.

---

## 🙌 Credits

- Waveshare (E-Ink hardware & driver libraries)
- Strava (API)
- Python / FastAPI / Uvicorn / Pillow
