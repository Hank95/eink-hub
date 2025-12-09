# From Dusty Raspberry Pi to Full-Stack Enlightenment: Building My Own Web Infrastructure

_How a simple e-ink calendar project turned into the web development education I never knew I needed_

---

## The Dream That Died (And Why That Was Okay)

Years ago, when I first started learning about web development, I had this dream: host my own website on a Raspberry Pi. No AWS bills, no Heroku, no middlemen—just my code, my hardware, my little corner of the internet.

Then I did the research.

SSL certificates. Port forwarding. DDoS protection. DNS configuration. Security hardening. The rabbit hole went deep, and at the bottom was a very real possibility of turning my home network into an open door for hackers. I quietly shelved the Pi and moved on.

Fast forward three years. I'm now a full-stack developer professionally. I work with React, Node, databases, APIs—the whole stack. But here's the thing about professional development: you're usually working on _part_ of something. You push code, it deploys somewhere magical, and users somehow reach it. The infrastructure is abstracted away. Someone else's problem.

Then came a cold, rainy day. I was cleaning out my closet and found it: the Raspberry Pi, still in its case, collecting dust. Something clicked.

## The Idea: Start Small

The original plan was modest—embarrassingly so. I just wanted a little e-ink calendar for my desk. No cloud services, no account signups, just a display that shows my schedule. The kind of project you finish in a weekend and forget about.

But I'm a web developer now. And I had questions.

_What if I want to control it from my phone?_

That means a web server.

_What if I want to see different views?_

That means an API and a frontend.

_What if I want to add weather data?_

That means external API calls and data persistence.

_What if I want to add my own sensors?_

That means... well, that means I'm building actual infrastructure.

The simple calendar became a dashboard. The dashboard needed a database. The database needed something to feed it. Before I knew it, I had ordered an ESP32 and a handful of sensors from Amazon.

## The Revelation: My Living Room Is a Sandbox

Here's what I realized: my local network is the perfect learning environment. It's the web development sandbox I always wanted but never knew I had.

Think about it:

- **No security risks** — Nothing is exposed to the internet
- **No costs** — No server bills, no domain fees
- **Full control** — I own every layer of the stack
- **Real hardware** — Not a simulation, not a tutorial, actual devices talking to each other

When you're learning web development through tutorials, everything is abstract. "The client makes a request to the server." Cool, but what does that _actually look like_? What happens in between?

Building this project, I finally understood. I could watch my ESP32 send an HTTP POST, see it hit my FastAPI server, watch it write to SQLite, then pull it back out through a GET request and render it in a chart. The full loop, visible and tangible.

## What We're Building

Here's what this "simple calendar" evolved into:

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│     ESP32       │  WiFi   │  Raspberry Pi   │  SPI    │   E-Ink Display │
│   + DHT11       │ ──────► │  + FastAPI      │ ──────► │   (7.5 inch)    │
│   + OLED        │         │  + SQLite       │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                    │
                                    ▼
                            ┌─────────────────┐
                            │  Web Dashboard  │
                            │  (any browser)  │
                            └─────────────────┘
```

The ESP32 reads temperature and humidity, sends it over WiFi to the Raspberry Pi. The Pi stores everything in SQLite, serves a web dashboard, and renders layouts on the e-ink display. Simple in concept, but touching every layer of the stack.

## Part 1: The Sensor Node (ESP32 + DHT11)

### Hardware

- ESP32 dev board (~$8)
- DHT11 temperature/humidity sensor (~$3)
- 0.96" OLED display (optional, ~$5)
- Breadboard and jumper wires

### Wiring

```
ESP32          DHT11
------         -----
3.3V    ───►   VCC
GND     ───►   GND
GPIO4   ───►   DATA

ESP32          OLED (I2C)
------         ----------
3.3V    ───►   VCC
GND     ───►   GND
GPIO21  ───►   SDA
GPIO22  ───►   SCL
```

### The Code

The ESP32 runs Arduino code that:

1. Connects to WiFi
2. Reads the DHT11 sensor every 2 seconds
3. Displays current readings on the OLED
4. POSTs data to the Raspberry Pi every 60 seconds

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);
Adafruit_SSD1306 display(128, 64, &Wire, -1);

const char* ssid = "YourWiFiName";
const char* password = "YourWiFiPassword";
const char* serverUrl = "http://YOUR_PI_IP:8000/api/sensor-data";

unsigned long lastSend = 0;
const unsigned long sendInterval = 60000; // 60 seconds

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  dht.begin();

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected! IP: " + WiFi.localIP().toString());
}

void loop() {
  float humidity = dht.readHumidity();
  float tempC = dht.readTemperature();
  float tempF = dht.readTemperature(true);

  if (!isnan(humidity) && !isnan(tempC)) {
    // Update OLED
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(2);
    display.setCursor(0, 0);
    display.print(tempF, 1);
    display.println(" F");
    display.setTextSize(1);
    display.print("Humidity: ");
    display.print(humidity, 1);
    display.println("%");
    display.display();

    // Send to server every 60 seconds
    if (millis() - lastSend >= sendInterval) {
      sendToServer(tempC, humidity);
      lastSend = millis();
    }
  }

  delay(2000); // DHT11 needs 2s between reads
}

void sendToServer(float tempC, float humidity) {
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  String payload = "{\"temperature_c\":" + String(tempC, 2) +
                   ",\"humidity\":" + String(humidity, 2) +
                   ",\"sensor_id\":\"esp32_dht11_1\"}";

  int responseCode = http.POST(payload);
  Serial.printf("POST response: %d\n", responseCode);
  http.end();
}
```

Flash this to your ESP32, and it'll start sending data to your Pi every minute.

## Part 2: The Server (Raspberry Pi + FastAPI)

The Raspberry Pi is the brains of the operation. It runs a Python web server that:

- Receives sensor data via HTTP POST
- Stores readings in SQLite
- Serves a web dashboard
- Renders layouts on the e-ink display

### Project Structure

```
eink-hub/
├── main.py                 # FastAPI app entry point
├── config.yaml             # Configuration file
├── sensors.db              # SQLite database (auto-created)
├── static/
│   ├── index.html          # Main dashboard
│   └── sensors.html        # Sensor history page
└── eink_hub/
    ├── api/
    │   ├── routes.py       # API endpoints
    │   └── models.py       # Pydantic models
    ├── core/
    │   ├── database.py     # SQLite wrapper
    │   ├── config.py       # Config loading
    │   └── scheduler.py    # Background jobs
    ├── providers/
    │   ├── indoor_sensor.py  # Reads from SQLite
    │   ├── weather.py        # OpenWeatherMap API
    │   └── ...
    ├── widgets/
    │   ├── indoor_sensor.py  # Renders sensor data
    │   └── ...
    └── display/
        └── driver.py       # E-ink hardware driver
```

### The Database Layer

When sensor data arrives, it goes straight into SQLite:

```python
# eink_hub/core/database.py

class SensorDatabase:
    def __init__(self, db_path="sensors.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    humidity REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def insert_reading(self, sensor_id, temperature_c, humidity):
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO sensor_readings (sensor_id, temperature_c, humidity) VALUES (?, ?, ?)",
                (sensor_id, temperature_c, humidity)
            )
            return cursor.lastrowid

    def get_latest_reading(self, sensor_id=None):
        # Returns the most recent reading
        ...

    def get_readings(self, sensor_id=None, hours=24):
        # Returns readings from the last N hours
        ...

    def get_stats(self, sensor_id=None, hours=24):
        # Returns min/max/avg for the period
        ...
```

### The API Endpoints

FastAPI makes it dead simple to define REST endpoints:

```python
# eink_hub/api/routes.py

from fastapi import APIRouter
from ..core.database import get_sensor_db

router = APIRouter(prefix="/api")

@router.post("/sensor-data")
async def receive_sensor_data(data: SensorDataRequest):
    """Receive data from ESP32."""
    db = get_sensor_db()
    reading_id = db.insert_reading(
        sensor_id=data.sensor_id,
        temperature_c=data.temperature_c,
        humidity=data.humidity,
    )
    return {"status": "ok", "reading_id": reading_id}

@router.get("/sensor-data")
async def get_sensor_data():
    """Get latest reading."""
    db = get_sensor_db()
    reading = db.get_latest_reading()
    # ... convert and return

@router.get("/sensor-data/history")
async def get_sensor_history(hours: int = 24):
    """Get historical readings for graphs."""
    db = get_sensor_db()
    readings = db.get_readings(hours=hours)
    stats = db.get_stats(hours=hours)
    return {"readings": readings, "stats": stats}
```

### Running the Server

```bash
# Install dependencies
pip install fastapi uvicorn pillow httpx apscheduler pydantic python-dotenv

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

The `--host 0.0.0.0` is crucial—it makes the server accessible from other devices on your network, not just localhost.

## Part 3: The Web Dashboard

The dashboard is a single HTML file with embedded CSS and JavaScript. No build tools, no npm, no React—just good old vanilla JS.

### How It Works

1. Browser loads `index.html` from the Pi
2. JavaScript calls `fetch('/api/sensor-data')` to get current readings
3. JavaScript calls `fetch('/api/sensor-data/history')` to get historical data
4. Chart.js renders beautiful graphs
5. Page auto-refreshes every 30 seconds

```html
<!-- static/sensors.html (simplified) -->
<!DOCTYPE html>
<html>
  <head>
    <title>Sensor History</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  </head>
  <body>
    <h1>Indoor Sensor History</h1>

    <div class="current-readings">
      <div class="reading-card">
        <div class="reading-value" id="current-temp">--</div>
        <div class="reading-label">Temperature</div>
      </div>
      <div class="reading-card">
        <div class="reading-value" id="current-humidity">--</div>
        <div class="reading-label">Humidity</div>
      </div>
    </div>

    <canvas id="tempChart"></canvas>

    <script>
      let tempChart;

      async function fetchData() {
        // Get current reading
        const current = await fetch("/api/sensor-data").then((r) => r.json());
        document.getElementById(
          "current-temp"
        ).textContent = `${current.temperature_f}°F`;
        document.getElementById(
          "current-humidity"
        ).textContent = `${current.humidity}%`;

        // Get history for chart
        const history = await fetch("/api/sensor-data/history?hours=24").then(
          (r) => r.json()
        );

        const chartData = history.readings.reverse().map((r) => ({
          x: new Date(r.timestamp),
          y: (r.temperature_c * 9) / 5 + 32,
        }));

        tempChart.data.datasets[0].data = chartData;
        tempChart.update();
      }

      // Initialize chart
      tempChart = new Chart(document.getElementById("tempChart"), {
        type: "line",
        data: {
          datasets: [
            {
              label: "Temperature (°F)",
              data: [],
              borderColor: "#e74c3c",
              fill: true,
            },
          ],
        },
        options: {
          scales: {
            x: { type: "time" },
          },
        },
      });

      // Fetch data now and every 30 seconds
      fetchData();
      setInterval(fetchData, 30000);
    </script>
  </body>
</html>
```

### The Advanced View

I also added a "Database Records" section that shows the raw SQLite data in a paginated table. It's hidden by default but super useful for debugging or just seeing what's happening under the hood.

Features:

- Toggle to show/hide
- Configurable time range (1h to 30 days)
- Pagination (25-250 rows per page)
- CSV export for data analysis

## Part 4: The E-Ink Display

This is where it gets fun. The Waveshare 7.5" e-ink display (800x480, black/white) gives the project that premium, always-on look without burning through power.

### The Widget System

Instead of hardcoding layouts, I built a widget system. Each widget knows how to render itself given some data:

```python
# eink_hub/widgets/indoor_sensor.py

@WidgetRegistry.register("indoor_sensor")
class IndoorSensorWidget(BaseWidget):
    def render(self, draw: ImageDraw, data: dict):
        temp = data.get("temperature_f", "--")
        humidity = data.get("humidity", "--")

        # Draw temperature
        temp_font = self._load_font(42, bold=True)
        draw.text((self.x, self.y), f"{temp}°F", font=temp_font, fill=0)

        # Draw humidity
        hum_font = self._load_font(24)
        draw.text((self.x, self.y + 50), f"{humidity}%", font=hum_font, fill=0)

        # Draw sparkline graph if enabled
        if self.options.get("show_graph") and "history" in data:
            self._draw_sparkline(draw, data["history"], ...)
```

### Layouts in YAML

Layouts are defined in `config.yaml`:

```yaml
layouts:
  indoor_climate:
    name: "Indoor Climate"
    widgets:
      - type: indoor_sensor
        x: 40
        y: 60
        width: 320
        height: 400
        provider: indoor_sensor
        options:
          show_graph: true
          show_stats: true

      - type: weather
        x: 420
        y: 60
        width: 340
        height: 180
        provider: weather

      - type: clock
        x: 420
        y: 280
        width: 340
        height: 80
```

### Rendering Pipeline

```
1. LayoutRenderer reads layout config
2. For each widget:
   a. Get data from the associated provider
   b. Create widget instance
   c. Call widget.render(draw, data)
3. Save PIL Image as PNG
4. Convert to 1-bit and send to e-ink display
```

The e-ink display takes about 2-3 seconds to refresh (it's e-ink, not LCD), so I only update it every few minutes or on manual trigger.

## Part 5: Putting It All Together

### Installation

```bash
# On the Raspberry Pi
git clone https://github.com/hp95/eink-hub.git
cd eink-hub

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy example config and edit
cp config.example.yaml config.yaml
nano config.yaml  # Add your API keys, WiFi, etc.

# Run!
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Auto-Start on Boot

Create a systemd service:

```ini
# /etc/systemd/system/eink-hub.service
[Unit]
Description=E-Ink Hub
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eink-hub
ExecStart=/home/pi/eink-hub/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable eink-hub
sudo systemctl start eink-hub
```

## Seeing the Whole Picture

After a few days of collecting data, something clicked that never quite had before in my professional work.

I was sitting at my desk, looking at the temperature graph on my phone. The humidity had spiked. I knew exactly why—I had just showered. But more importantly, I knew exactly _how_ I knew:

1. The DHT11 sensor detected the humidity change
2. The ESP32 read that value and constructed a JSON payload
3. An HTTP POST traveled over my WiFi to 10.0.0.140:8000
4. FastAPI's route decorator matched `/api/sensor-data` to my handler function
5. Pydantic validated the incoming data against my schema
6. SQLite wrote a row to the `sensor_readings` table
7. My browser's `setInterval` triggered a `fetch()` call
8. The API queried SQLite and serialized the response to JSON
9. Chart.js parsed the data and re-rendered the graph
10. I saw the spike

I've built features at work that do similar things. But I've never _seen_ all of it at once. The layers are usually hidden behind deployment pipelines, managed databases, and team boundaries.

Here, in my living room, I own every layer. When something breaks, I can't blame DevOps. When something works, I know exactly why.

## The Education I Didn't Know I Needed

Three years of professional development taught me how to ship software. This project reminded me what’s actually happening underneath all the abstractions we usually work with.

**HTTP isn’t magic** — it’s just text over a socket. When the ESP32 hits my endpoint with POST /api/sensor-data HTTP/1.1, I can literally watch that raw string land in the server logs. Seeing it unmediated by frameworks makes the whole request/response loop feel simple and tangible.

**A database can just be a file.** SQLite lives as a single file on disk. You can copy it, inspect it, email it, open it in a GUI. No container, no cluster, no connection pool. It’s a good reminder that persistence doesn’t always need infrastructure.

**Frontend and backend are more alike than they seem.** At the end of the day they’re just runtimes exchanging text. The browser runs JavaScript, Python runs on the server, and they talk over HTTP. Different environments, same fundamental idea.

**The “full stack” actually goes further than the diagram.** It extends down to GPIO pins and sensor data, and up to CSS animations and UI polish. Touching each layer end-to-end makes every part of the system easier to reason about.

## What's Next?

The project keeps growing:

- **More sensors** — I want ESP32 nodes in different rooms
- **Alerts** — Push notifications when temp/humidity goes out of range
- **Historical analysis** — What's the temperature pattern over a whole year?
- **More displays** — Maybe a small one for the kitchen?

But honestly, the "what's next" matters less than the foundation I've built. I now have a mental model of web infrastructure that I can apply anywhere. The next time I'm debugging a production issue at work, I'll be thinking about HTTP requests and database queries in a much more concrete way.

## For the Aspiring Self-Hosters

If you're like me years ago—dreaming of self-hosting but scared of the security implications—consider this approach:

**Start local.**

You don't need to expose anything to the internet to learn how the internet works. Your home network is a perfect sandbox. Build something useful for yourself. Control it from your phone. Watch the requests flow. Add a database. Add another device.

By the time you're ready to expose something to the world (if you ever want to), you'll actually understand what you're exposing. You'll know what ports do, what HTTPS protects, why databases shouldn't be public. Not because a tutorial told you, but because you've seen the alternative.

The dusty Raspberry Pi in your closet isn't just a hobby project. It's a learning environment with zero monthly fees, zero security risks, and unlimited potential.

Go blow the dust off. See what happens.

---

_The total cost of this project was under $100. The education was priceless._

---

_Tags: ESP32, Raspberry Pi, E-Ink, Home Automation, Python, FastAPI, Web Development, Learning, DIY Electronics_
