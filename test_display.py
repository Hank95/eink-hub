from waveshare_epd import epd7in5_V2
from PIL import Image, ImageDraw, ImageFont

print("Initializing display...")
epd = epd7in5_V2.EPD()
epd.init()

# Optional clear
epd.Clear()

# Create 1-bit (B/W) image
image = Image.new('1', (epd.width, epd.height), 255)
draw = ImageDraw.Draw(image)

# Border so we know orientation
draw.rectangle((5, 5, epd.width - 5, epd.height - 5), outline=0, width=3)

# Load font
try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48
    )
except Exception:
    font = ImageFont.load_default()

text = "Hello Hank!"

# Use Pillow 10+ compatible text size
bbox = draw.textbbox((0, 0), text, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]

x = (epd.width - text_w) // 2
y = (epd.height - text_h) // 2

# White box behind text
padding = 20
draw.rectangle(
    (x - padding, y - padding, x + text_w + padding, y + text_h + padding),
    fill=255, outline=0, width=2
)

# Draw black text
draw.text((x, y), text, font=font, fill=0)

print("Displaying...")
epd.display(epd.getbuffer(image))

print("Sleeping...")
epd.sleep()

print("Done.")
