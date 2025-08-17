from machine import Pin, SPI
from waveshare2in7 import BLACK, EPD, WHITE
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


def demo():
    print("Hello!")
    epd = EPD(spi, cs, dc, rst, busy, orientation=1, debug=True)
    epd.init()
    epd.fill(WHITE)
    epd.draw_bmp("david.bmp", 0, 0)
    epd.display()
    time.sleep(3)

    for orientation in [0, 2, 3, 1]:
        print(f"Orientation: {orientation}")
        epd = EPD(spi, cs, dc, rst, busy, orientation=orientation, debug=True)
        epd.init()
        epd.fill(WHITE)  # Fill frame buffer with white
        epd.fill_rect(10, 10, 20, 20, BLACK)
        epd.text("Hello World!", 10, 40, BLACK)
        epd.text(f"Orientation: {orientation}", 10, 60, BLACK)
        epd.display()
        time.sleep(3)

    print("Done")


if __name__ == "__main__":
    demo()
