# /*****************************************************************************
# * | File        :	  epdconfig.py
# * | Author      :   Waveshare team
# * | Function    :   Hardware underlying interface
# * | Info        :
# *----------------
# * | This version:   V1.2
# * | Date        :   2022-10-29
# * | Info        :   
# ******************************************************************************
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# epdconfig.py - simplified Raspberry Pi config for Waveshare e-Paper
# Uses RPi.GPIO + spidev directly (no gpiozero).

# epdconfig.py - Raspberry Pi config for Waveshare e-Paper (7.5" V2)
# Simple, driver-compatible version using RPi.GPIO + spidev.

# epdconfig.py - Raspberry Pi config for Waveshare 7.5" V2 e-Paper
# Uses RPi.GPIO + spidev, no gpiozero.

import time

import spidev
import RPi.GPIO as GPIO


class RaspberryPi(object):
    # BCM pin numbers (Waveshare standard)
    RST_PIN = 17
    DC_PIN = 25
    CS_PIN = 8
    BUSY_PIN = 24

    def __init__(self):
        # Set up GPIO once
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(self.RST_PIN, GPIO.OUT)
        GPIO.setup(self.DC_PIN, GPIO.OUT)
        GPIO.setup(self.CS_PIN, GPIO.OUT)
        GPIO.setup(self.BUSY_PIN, GPIO.IN)

        # Set up SPI once
        self.SPI = spidev.SpiDev()
        # bus 0, device 0 (CE0)
        self.SPI.open(0, 0)
        self.SPI.max_speed_hz = 2000000
        self.SPI.mode = 0b00

    # --- Low-level helpers ---

    def digital_write(self, pin, value):
        GPIO.output(pin, value)

    def digital_read(self, pin):
        return GPIO.input(pin)

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        # data: list of ints/bytes
        self.SPI.writebytes(list(data))

    def spi_writebyte2(self, data):
        # Some systems have a 4096-byte limit; send in chunks
        buf = list(data)
        MAX_CHUNK = 4096
        for i in range(0, len(buf), MAX_CHUNK):
            self.SPI.writebytes(buf[i:i + MAX_CHUNK])

    def module_exit(self):
        # For long-running apps (like your FastAPI server),
        # don't call GPIO.cleanup() here or it will break
        # the next use of the display.
        try:
            self.SPI.close()
        except Exception:
            pass
        # NOTE: no GPIO.cleanup() on purpose

# Single global instance
implementation = RaspberryPi()


# Wrapper so epd7in5_V2 can call epdconfig.SPI.writebytes2(...)
class _SPIWrapper:
    def __init__(self, impl):
        self._impl = impl

    def writebytes(self, data):
        self._impl.spi_writebyte(data)

    def writebytes2(self, data):
        self._impl.spi_writebyte2(data)


# This is what epd7in5_V2 expects to exist:
SPI = _SPIWrapper(implementation)

# Expose pin constants if any driver needs them
RST_PIN = implementation.RST_PIN
DC_PIN = implementation.DC_PIN
CS_PIN = implementation.CS_PIN
BUSY_PIN = implementation.BUSY_PIN


# --- Functions used by epd7in5_V2.py ---

def digital_write(pin, value):
    implementation.digital_write(pin, value)


def digital_read(pin):
    return implementation.digital_read(pin)


def delay_ms(delaytime):
    implementation.delay_ms(delaytime)


def spi_writebyte(data):
    implementation.spi_writebyte(data)


def spi_writebyte2(data):
    implementation.spi_writebyte2(data)


def module_init():
    """
    Driver calls this before use. We've already initialized everything
    in the global 'implementation', so just return 0 for success.
    """
    return 0

def module_exit():
    # No-op for now; we don't want to tear down GPIO in a server context
    return 0

### END OF FILE ###
