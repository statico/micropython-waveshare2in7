"""
Demo script for 2.7 inch e-paper display
Shows text, shapes, and patterns
"""

from machine import Pin, SPI
from waveshare2in7 import EPD
import time

# WaveShare 2.7" E-Paper Display to ESP-WROOM-32
# GND     → GND
# VCC     → 3.3V
# CS      → GPIO 5 (or any available GPIO)
# CLK     → GPIO 18 (default SPI CLK)
# DIN     → GPIO 23 (default SPI MOSI)
# DC      → GPIO 2 (or any available GPIO)
# RST     → GPIO 4 (or any available GPIO)
# BUSY    → GPIO 15 (or any available GPIO)
spi = SPI(2, baudrate=4000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23))
cs = Pin(5, Pin.OUT)
dc = Pin(2, Pin.OUT)
rst = Pin(4, Pin.OUT)
busy = Pin(15, Pin.IN)

def demo(orientation=0):
    """Run a demo on the e-paper display"""
    print("Starting e-paper display demo...")


    print("Creating display object...")
    epd = EPD(spi, cs, dc, rst, busy, orientation=orientation)

    # Initialize the display
    epd.init()

    # Simple test - clear to white, then draw some content
    print("Clearing display to white...")
    epd.clear()

    # Draw some text
    print("Drawing text...")
    epd.fill(0xFF)  # Clear frame buffer to white
    epd.fill_rect(10, 10, 100, 50, 0x00)
    epd.text("Hello World!", 10, 10, 0x00)
    epd.text("E-Paper Display", 10, 30, 0x00)
    epd.text("Working!", 10, 50, 0x00)
    epd.display()
    time.sleep(3)

    # Draw some shapes
    print("Drawing shapes...")
    epd.fill(0xFF)  # Clear frame buffer to white
    epd.rect(10, 10, 100, 50, 0x00)  # Rectangle
    epd.fill_rect(120, 10, 50, 50, 0x00)  # Filled rectangle
    epd.circle(200, 35, 25, 0x00)  # Circle
    epd.line(10, 80, 200, 80, 0x00)  # Line
    epd.display()
    time.sleep(3)

    # Draw a pattern
    print("Drawing pattern...")
    epd.fill(0xFF)  # Clear frame buffer to white
    # Draw vertical lines
    for i in range(0, epd.width, 20):
        epd.line(i, 0, i, epd.height, 0x00)
    # Draw horizontal lines
    for i in range(0, epd.height, 20):
        epd.line(0, i, epd.width, i, 0x00)
    epd.display()
    time.sleep(3)

    # Fill with black
    print("Filling with black...")
    epd.fill_black()

    print("✓ Demo completed!")
    print("You should have seen text, shapes, and patterns!")


if __name__ == "__main__":
    while True:
      demo(0)
      time.sleep(3)
      demo(1)
      time.sleep(3)
      demo(2)
      time.sleep(3)
      demo(3)
      time.sleep(3)
