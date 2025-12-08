# Raspberry Pi E-Ink Hub — One‑Page Cheat Sheet

## 🔑 SSH Into Pi
```bash
ssh hp95@HPPI
# or
ssh hp95@10.0.0.xxx
```

## 📁 Go to Project
```bash
cd ~/dev/eink-hub
```

## 🧪 Activate Virtual Environment
```bash
source ~/dev/dashboard/eink/venv/bin/activate
```

You should see:
```
(venv) hp95@HPPI:~/dev/eink-hub $
```

## 🚀 Start the Server
```bash
sudo /home/hp95/dev/dashboard/eink/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

Access from laptop:
```
http://HPPI.local:8000
```
or
```
http://10.0.0.xxx:8000
```

## 🔄 Restart Server After Code Changes
Stop:
```
Ctrl + C
```

Restart:
```bash
sudo /home/hp95/dev/dashboard/eink/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🎨 Test E‑Ink Display
```bash
python3 test_display.py
```

## 🖼 Test Layout Rendering
Render previews:
```bash
python3 layouts.py
```

Send a layout manually:
```bash
curl -X POST http://localhost:8000/api/display   -H "Content-Type: application/json"   -d '{"layout": "daily_rundown"}'
```

## 🤝 Use Claude on the Pi
Ask questions:
```bash
claude "Explain render_strava_dashboard."
```

Edit a file:
```bash
claude --edit layouts.py
```

Debug errors:
```bash
claude "Fix this:" < error.log
```

## 📦 Pull Latest Code
```bash
git pull
pip install -r requirements.txt
```

## 📤 Push Pi‑Side Changes
```bash
git add .
git commit -m "Changes from Pi"
git push
```

## ⚠️ Common Fixes
Reset Pi:
```bash
sudo reboot
```

Install fonts:
```bash
sudo apt install fonts-dejavu-core
```

## 📂 Project Structure
```
eink-hub/
  main.py
  layouts.py
  eink_driver.py
  strava_client.py
  static/
  previews/
  uploads/
  waveshare_epd/
```
