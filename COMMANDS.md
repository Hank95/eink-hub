# E-Ink Hub - Useful Commands

Quick reference for managing and interacting with the E-Ink Hub project.

---

## Service Management

```bash
# Check if the service is running
sudo systemctl status eink-hub

# Start the service
sudo systemctl start eink-hub

# Stop the service
sudo systemctl stop eink-hub

# Restart the service (after code changes)
sudo systemctl restart eink-hub

# View live logs
sudo journalctl -u eink-hub -f

# View last 100 log lines
sudo journalctl -u eink-hub -n 100

# Disable auto-start on boot
sudo systemctl disable eink-hub

# Re-enable auto-start on boot
sudo systemctl enable eink-hub
```

---

## API Endpoints

All endpoints are available at `http://<pi-ip>:8000`

### Display Control

```bash
# Get current status (layout, mode, providers)
curl http://localhost:8000/api/status

# List available layouts
curl http://localhost:8000/api/layouts

# Send a layout to the e-ink display
curl -X POST http://localhost:8000/api/display \
  -H "Content-Type: application/json" \
  -d '{"layout": "composite_hub"}'

# Available layouts:
#   - composite_hub     (main dashboard)
#   - indoor_climate    (sensor focus with graphs)
#   - weather_view      (full weather display)
#   - week_view         (calendar week view)
#   - strava_dashboard  (running stats)
#   - daily_rundown     (calendar + weather)

# Switch to manual mode
curl -X POST http://localhost:8000/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "manual"}'

# Switch to auto-rotate mode
curl -X POST http://localhost:8000/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "auto_rotate"}'

# Get current preview image
curl http://localhost:8000/api/preview --output preview.png
```

### Sensor Data

```bash
# Get latest sensor reading
curl http://localhost:8000/api/sensor-data

# Get sensor history (last 24 hours)
curl "http://localhost:8000/api/sensor-data/history?hours=24"

# Get sensor history (last 7 days)
curl "http://localhost:8000/api/sensor-data/history?hours=168"

# List all known sensors
curl http://localhost:8000/api/sensor-data/sensors

# Manually send sensor data (like the ESP32 does)
curl -X POST http://localhost:8000/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"temperature_c": 22.5, "humidity": 45.0, "sensor_id": "test_sensor"}'
```

### Provider Management

```bash
# List all providers and their status
curl http://localhost:8000/api/providers

# Manually refresh a provider
curl -X POST http://localhost:8000/api/refresh/weather
curl -X POST http://localhost:8000/api/refresh/indoor_sensor
curl -X POST http://localhost:8000/api/refresh/calendar
curl -X POST http://localhost:8000/api/refresh/strava

# Reload configuration (after editing config.yaml)
curl -X POST http://localhost:8000/api/reload-config

# List scheduled jobs
curl http://localhost:8000/api/jobs
```

---

## Web Dashboard URLs

```
Main Dashboard:     http://<pi-ip>:8000/
Sensor History:     http://<pi-ip>:8000/sensors
API Documentation:  http://<pi-ip>:8000/docs
```

---

## Database Commands

```bash
# Open the SQLite database
sqlite3 sensors.db

# Inside sqlite3:
.tables                              # List tables
.schema sensor_readings              # Show table structure
SELECT COUNT(*) FROM sensor_readings;  # Count total readings
SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 10;  # Last 10 readings
.quit                                # Exit

# One-liner: count readings
sqlite3 sensors.db "SELECT COUNT(*) FROM sensor_readings;"

# One-liner: last 5 readings
sqlite3 sensors.db "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 5;"

# Backup the database
cp sensors.db sensors_backup_$(date +%Y%m%d).db

# Export to CSV
sqlite3 -header -csv sensors.db "SELECT * FROM sensor_readings;" > sensor_export.csv
```

---

## Log Files

```bash
# Application log
tail -f logs/eink-hub.log

# Last 50 lines of app log
tail -50 logs/eink-hub.log

# Search logs for errors
grep -i error logs/eink-hub.log

# Search logs for a specific sensor
grep "esp32_dht11" logs/eink-hub.log
```

---

## Configuration

```bash
# Edit main configuration
nano config.yaml

# After editing, reload without restart:
curl -X POST http://localhost:8000/api/reload-config

# Or restart the service:
sudo systemctl restart eink-hub

# Edit environment variables
nano .env
# (requires service restart)
```

---

## Development

```bash
# Run server manually (foreground, for debugging)
cd /home/hp95/dev/eink-hub
/home/hp95/dev/dashboard/eink/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Check Python syntax
python3 -c "import ast; ast.parse(open('main.py').read())"

# Test a specific module
python3 -c "from eink_hub.core.database import get_sensor_db; print('OK')"
```

---

## ESP32 Sensor

The ESP32 sends data to:
```
POST http://<pi-ip>:8000/api/sensor-data
Content-Type: application/json

{"temperature_c": 23.5, "humidity": 45.2, "sensor_id": "esp32_dht11_1"}
```

To test if the Pi is receiving data:
```bash
# Watch for incoming sensor data in real-time
sudo journalctl -u eink-hub -f | grep "Sensor data received"
```

---

## Troubleshooting

```bash
# Service won't start - check logs
sudo journalctl -u eink-hub -n 50 --no-pager

# Check if port 8000 is in use
sudo lsof -i :8000

# Kill process on port 8000
sudo fuser -k 8000/tcp

# Check disk space (SQLite can grow)
df -h

# Check database size
ls -lh sensors.db

# Test network connectivity from ESP32's perspective
# (run on another machine)
curl http://<pi-ip>:8000/api/status

# Restart everything fresh
sudo systemctl stop eink-hub
sudo systemctl start eink-hub
sudo systemctl status eink-hub
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start server | `sudo systemctl start eink-hub` |
| Stop server | `sudo systemctl stop eink-hub` |
| View logs | `sudo journalctl -u eink-hub -f` |
| Check status | `curl localhost:8000/api/status` |
| Change display | `curl -X POST localhost:8000/api/display -H "Content-Type: application/json" -d '{"layout": "indoor_climate"}'` |
| Refresh sensor | `curl -X POST localhost:8000/api/refresh/indoor_sensor` |
| Latest reading | `curl localhost:8000/api/sensor-data` |
| Sensor history | `curl "localhost:8000/api/sensor-data/history?hours=24"` |
| Open dashboard | `http://<pi-ip>:8000/` |
| Sensor graphs | `http://<pi-ip>:8000/sensors` |
