# MicroPython Waveshare 2.7" E-Paper Display Driver

A MicroPython driver for the [Waveshare 2.7" Black/White e-paper display](https://www.waveshare.com/wiki/2.7inch_e-Paper_HAT). This library provides full control over the display with support for multiple orientations, optimized SPI transfers, and a rich set of graphics functions.

![epaper](https://github.com/user-attachments/assets/24d8bf74-448c-4cfd-93c4-8e0f8e35fe04)

NOTE: This was mostly vibe coded with Cursor and Claude Code by pointing it at [the Waveshare Arduino library](https://github.com/waveshareteam/e-Paper/tree/master/Arduino/epd2in7b_V2) and saying "make it do the thing."

Purchase links (referral-free):

- [Waveshare 2.7" Black/White e-paper display](https://a.co/d/1f9ir2h)
- [ESP-WROOM-32 development board](https://a.co/d/9ut4h8a)

## Features

- **Full Display Control**: Complete initialization, display updates, and power management
- **Multiple Orientations**: Support for 0°, 90°, 180°, and 270° rotation
- **Optimized Performance**: Batch SPI transfers and efficient memory usage
- **Rich Graphics API**: Text, shapes, lines, rectangles, circles, and BMP image support
- **Debug Mode**: Optional debug logging for development and troubleshooting
- **Power Management**: Deep sleep mode and proper power cycling
- **Memory Efficient**: Optimized frame buffer handling for MicroPython environments

## Hardware Requirements

- Waveshare 2.7" E-Paper Display (GDEW027W3)
- ESP32 or compatible MicroPython board
- SPI interface support

## Pin Connections

| Display Pin | ESP32 Pin | Description  |
| ----------- | --------- | ------------ |
| GND         | GND       | Ground       |
| VCC         | 3.3V      | Power        |
| CS          | GPIO 5    | Chip Select  |
| CLK         | GPIO 18   | SPI Clock    |
| DIN         | GPIO 23   | SPI MOSI     |
| DC          | GPIO 2    | Data/Command |
| RST         | GPIO 4    | Reset        |
| BUSY        | GPIO 15   | Busy Signal  |

## Quick Start

Create a virutal environment with [uv](https://docs.astral.sh/uv/) and install the dependencies:

```shell
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
mpremote --version
```

Copy and run the library and `main.py` for a demo:

```shell
mpremote cp -r waveshare2in7.py david.bmp :
mpremote run main.py
```

## API Reference

### EPD Class

#### Constructor

```python
EPD(spi, cs, dc, rst, busy, orientation=0, debug=False)
```

**Parameters:**

- `spi`: SPI bus instance
- `cs`: Chip select pin
- `dc`: Data/command pin
- `rst`: Reset pin
- `busy`: Busy signal pin
- `orientation`: Display orientation (0, 1, 2, 3 for 0°, 90°, 180°, 270°)
- `debug`: Enable debug logging

#### Core Methods

##### `init()`

Initialize the display with proper power-up sequence.

##### `display()`

Display the current frame buffer content.

##### `clear()`

Clear the display to white using optimized method.

##### `fill_black()`

Fill the display with black using optimized method.

##### `sleep()`

Put the display into deep sleep mode to save power.

##### `reset_display()`

Hardware reset and re-initialize the display.

#### Graphics Methods

##### `fill(color)`

Fill the entire frame buffer with the specified color.

##### `text(string, x, y, color=BLACK)`

Draw text at the specified coordinates.

##### `line(x1, y1, x2, y2, color=BLACK)`

Draw a line between two points.

##### `rect(x, y, w, h, color=BLACK)`

Draw a rectangle outline.

##### `fill_rect(x, y, w, h, color=BLACK)`

Draw a filled rectangle.

##### `circle(x, y, radius, color=BLACK)`

Draw a circle using optimized Bresenham's algorithm.

##### `vline(x, y, h, color=BLACK)`

Draw a vertical line.

##### `hline(x, y, w, color=BLACK)`

Draw a horizontal line.

##### `draw_bmp(filename, x, y)`

Display a 1-bit BMP file at the specified coordinates.

#### Orientation Control

##### `set_orientation(orientation)`

Change display orientation without reinitializing.

**Orientations:**

- `0`: Portrait (176×264)
- `1`: Landscape (264×176)
- `2`: Portrait upside down (176×264)
- `3`: Landscape upside down (264×176)

## Examples

### Basic Text Display

```python
epd = EPD(spi, cs, dc, rst, busy)
epd.init()
epd.fill(WHITE)
epd.text("Hello World!", 10, 40, BLACK)
epd.text("MicroPython", 10, 60, BLACK)
epd.display()
```

### Graphics Demo

```python
epd = EPD(spi, cs, dc, rst, busy)
epd.init()
epd.fill(WHITE)

# Draw shapes
epd.rect(10, 10, 50, 30, BLACK)
epd.fill_rect(70, 10, 50, 30, BLACK)
epd.circle(100, 100, 20, BLACK)
epd.line(10, 150, 100, 200, BLACK)

# Draw text
epd.text("Graphics Demo", 10, 250, BLACK)
epd.display()
```

### Orientation Demo

```python
for orientation in [0, 1, 2, 3]:
    epd = EPD(spi, cs, dc, rst, busy, orientation=orientation)
    epd.init()
    epd.fill(WHITE)
    epd.text(f"Orientation: {orientation}", 10, 40, BLACK)
    epd.fill_rect(10, 60, 30, 30, BLACK)
    epd.display()
    time.sleep(3)
```

### BMP Image Display

```python
epd = EPD(spi, cs, dc, rst, busy)
epd.init()
epd.fill(WHITE)
epd.draw_bmp("image.bmp", 0, 0)  # Display 1-bit BMP
epd.display()
```

## Technical Details

### Display Specifications

- **Resolution**: 176×264 pixels (portrait mode)
- **Display Type**: E-paper (GDEW027W3)
- **Colors**: Black and White only
- **Refresh Time**: ~2-3 seconds
- **Power**: 3.3V operation

### Memory Usage

- Frame buffer size: ~5.8KB (176×264÷8 bytes)
- Optimized for MicroPython memory constraints
- Batch SPI transfers for better performance

### Performance Optimizations

- SPI batch transfers (64-byte chunks)
- Efficient coordinate transformations for rotations
- Optimized clear and fill operations
- Minimal memory allocations

## Troubleshooting

### Common Issues

1. **Display not responding**: Check power connections and reset pin
2. **Garbled display**: Verify SPI settings and pin connections
3. **Slow performance**: Ensure proper SPI baudrate (4MHz recommended)
4. **Memory errors**: Check available RAM on your MicroPython device

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
epd = EPD(spi, cs, dc, rst, busy, debug=True)
```

## License

MIT License

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this library.

## Acknowledgments

- Based on Waveshare's Arduino e-paper library
- Optimized for MicroPython performance and memory constraints
- Enhanced with additional graphics functions and orientation support
