"""
MicroPython Waveshare 2.7" Black/White GDEW027W3 e-paper display driver

Base on https://github.com/waveshareteam/e-Paper/tree/master/Arduino/epd2in7b_V2 and mostly but not entirely vibe coded with Cursor
"""

from micropython import const
from time import sleep_ms, ticks_ms
import framebuf
import struct

WHITE = const(0xFF)
BLACK = const(0x00)

# Display resolution (portrait mode) - corrected to match Arduino
EPD_WIDTH = const(176)
EPD_HEIGHT = const(264)

# Display commands
PANEL_SETTING = const(0x00)
POWER_SETTING = const(0x01)
POWER_ON = const(0x04)
BOOSTER_SOFT_START = const(0x06)
DEEP_SLEEP = const(0x07)
DATA_START_TRANSMISSION_1 = const(0x10)
DISPLAY_REFRESH = const(0x12)
DATA_START_TRANSMISSION_2 = const(0x13)
PARTIAL_DISPLAY_REFRESH = const(0x16)
LUT_FOR_VCOM = const(0x20)
LUT_WHITE_TO_WHITE = const(0x21)
LUT_BLACK_TO_WHITE = const(0x22)
LUT_WHITE_TO_BLACK = const(0x23)
LUT_BLACK_TO_BLACK = const(0x24)
PLL_CONTROL = const(0x30)
VCM_DC_SETTING_REGISTER = const(0x82)
POWER_OPTIMIZATION = const(0xF8)

BUSY = const(0)  # 0=busy, 1=idle

# Optimization constants
SPI_BATCH_SIZE = const(64)  # Optimal batch size for SPI transfers


class EPD:
    def __init__(self, spi, cs, dc, rst, busy, orientation=0, debug=False):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.busy = busy
        self.orientation = orientation
        self.debug = debug

        # Initialize pins properly
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        self.rst.init(self.rst.OUT, value=0)
        self.busy.init(self.busy.IN)

        # Always use original portrait dimensions for the frame buffer
        # The display hardware expects data in portrait format regardless of orientation
        buffer_size = (self.width * self.height + 7) // 8
        self.buffer = bytearray(buffer_size)
        self.framebuf = framebuf.FrameBuffer(
            self.buffer, self.width, self.height, framebuf.MONO_HLSB
        )

    def _log(self, message):
        if self.debug:
            print(f"[EPD] {ticks_ms()}ms: {message}")

    @property
    def width(self):
        """Get display width based on current orientation"""
        return EPD_WIDTH if self.orientation % 2 == 0 else EPD_HEIGHT

    @property
    def height(self):
        """Get display height based on current orientation"""
        return EPD_HEIGHT if self.orientation % 2 == 0 else EPD_WIDTH

    def set_orientation(self, orientation):
        """Change orientation without reinitializing"""
        self._log(f"Setting orientation to {orientation}")
        self.orientation = orientation

    def _command(self, command, data=None):
        """Send command to display"""
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([command]))
        self.cs(1)
        if data is not None:
            self._data(data)

    def _data(self, data):
        """Send data to display - optimized for single byte"""
        self.dc(1)
        self.cs(0)
        if isinstance(data, int):
            self.spi.write(bytearray([data]))
        else:
            self.spi.write(data)
        self.cs(1)

    def _data_batch(self, data_list):
        """Send data in batches for better SPI performance"""
        if not data_list:
            return

        self.dc(1)
        self.cs(0)

        # Convert list to bytearray for efficient transfer
        if isinstance(data_list, list):
            data_bytes = bytearray(data_list)
        else:
            data_bytes = data_list

        self.spi.write(data_bytes)
        self.cs(1)

    def _clear_display_fast(self):
        """Fast clear using display commands instead of frame buffer"""
        self._log("Fast clearing display")

        # Set RAM address counters
        self._command(0x4E)
        self._data(0x00)
        self._command(0x4F)
        self._data(0x00)
        self._data(0x00)

        # Write RAM for black/white
        self._command(0x24)

        # Send all white bytes in batches
        buffer_size = len(self.buffer)
        batch_size = SPI_BATCH_SIZE
        white_data = [0xFF] * batch_size

        for i in range(0, buffer_size, batch_size):
            end = min(i + batch_size, buffer_size)
            if end - i == batch_size:
                # Full batch
                self._data_batch(white_data)
            else:
                # Partial batch
                partial_data = [0xFF] * (end - i)
                self._data_batch(partial_data)

    def init(self):
        """Initialize display using corrected sequence"""
        self._log("Initializing display")

        # Reset
        self.rst(1)
        sleep_ms(200)
        self.rst(0)
        sleep_ms(2)
        self.rst(1)
        sleep_ms(200)

        # Send initialization commands - corrected sequence
        self._command(0x12)  # Soft reset
        sleep_ms(10)

        self._command(0x01)  # Driver output control
        self._data(0xB7)
        self._data(0x01)
        self._data(0x00)

        self._command(0x11)  # Data entry mode
        self._data(0x03)  # Corrected to match Arduino

        self._command(0x44)  # Set RAM X address start/end
        self._data(0x00)
        self._data(0x15)  # 0x15-->(21+1)*8=176 (from Arduino)

        self._command(0x45)  # Set RAM Y address start/end
        self._data(0x00)
        self._data(0x00)
        self._data(0x07)  # 0x0107-->(263+1)=264
        self._data(0x01)

        self._command(0x3C)  # Border waveform control
        self._data(0x05)

        self._command(0x18)  # Temperature sensor control
        self._data(0x80)

        # Power management
        self._command(0x22)  # Display update control
        self._data(0xB1)
        self._command(0x20)

        # Set RAM address counters
        self._command(0x4E)  # Set RAM X address counter
        self._data(0x00)
        self._command(0x4F)  # Set RAM Y address counter
        self._data(0x00)
        self._data(0x00)

        self._log("Display initialized")

    def wait_until_idle(self):
        """Wait until display is not busy"""
        self._log("Waiting until display is not busy...")
        while self.busy.value() == BUSY:
            sleep_ms(100)
        self._log("Display is not busy")

    def display_frame(self, frame_buffer):
        """Display frame buffer with proper orientation handling and optimized SPI"""
        self._log("Displaying frame")

        # Clear any previous data
        self._command(0x24)  # Write RAM for black/white
        for i in range(0, len(frame_buffer)):
            self._data(0xFF)  # Clear to white first

        # Set RAM X address counter
        self._command(0x4E)
        self._data(0x00)

        # Set RAM Y address counter
        self._command(0x4F)
        self._data(0xB7)
        self._data(0x01)

        # Write RAM for black/white
        self._command(0x24)

        # Get original display dimensions (portrait)
        orig_width = EPD_WIDTH

        if self.orientation == 0:
            self._log("Displaying frame in portrait mode")
            # Default portrait mode - send data in batches
            self._send_buffer_batched(frame_buffer)

        elif self.orientation == 2:
            self._log("Displaying frame in portrait upside down mode")
            # Portrait upside down - reverse byte order and flip bits
            flipped_buffer = bytearray(len(frame_buffer))
            for i in range(len(frame_buffer)):
                # Flip bits in each byte (reverse bit order)
                byte_val = frame_buffer[i]
                flipped_byte = 0
                for bit in range(8):
                    if byte_val & (1 << bit):
                        flipped_byte |= 1 << (7 - bit)
                flipped_buffer[len(frame_buffer) - 1 - i] = flipped_byte
            self._send_buffer_batched(flipped_buffer)

        elif self.orientation == 1:
            self._log("Displaying frame in landscape mode")
            rotated_buffer = self._rotate_buffer_90_cw(frame_buffer)
            self._send_buffer_batched(rotated_buffer)

        elif self.orientation == 3:
            self._log("Displaying frame in landscape upside down mode")
            rotated_buffer = self._rotate_buffer_270_cw(frame_buffer)
            self._send_buffer_batched(rotated_buffer)

        # Display update control
        self._log("Display update control")
        self._command(0x22)
        self._data(0xC7)
        self._command(0x20)  # Master activation
        self.wait_until_idle()

    def _send_buffer_batched(self, buffer):
        """Send buffer data in optimized batches"""
        batch_size = SPI_BATCH_SIZE
        for i in range(0, len(buffer), batch_size):
            end = min(i + batch_size, len(buffer))
            batch_data = buffer[i:end]
            self._data_batch(batch_data)

    def _rotate_buffer_90_cw(self, logical_buffer):
        """Rotate buffer 90° clockwise with optimized algorithm"""
        # Physical buffer for actual display dimensions (176x264)
        physical_buffer_size = (EPD_WIDTH * EPD_HEIGHT + 7) // 8
        physical_buffer = bytearray(physical_buffer_size)

        def logical_to_physical(x, y):
            # Rotate 90° clockwise: logical (264w×176h) -> physical (176w×264h)
            # For 90° clockwise: (x,y) -> (y, width-1-x)
            new_x = y
            new_y = self.width - 1 - x  # self.width is 264 in landscape mode
            return new_x, new_y

        def get_logical_pixel(x, y):
            # Get pixel from logical buffer (landscape: 264×176)
            bit_index = y * self.width + x
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            return (logical_buffer[byte_index] >> (7 - bit_offset)) & 1

        def set_physical_pixel(x, y, value):
            # Set pixel in physical buffer (portrait: 176×264)
            bit_index = y * EPD_WIDTH + x
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            if value:
                physical_buffer[byte_index] |= 1 << (7 - bit_offset)
            else:
                physical_buffer[byte_index] &= ~(1 << (7 - bit_offset))

        # Transform from logical coordinates to physical coordinates
        self._log("Transforming coordinates")
        for ly in range(self.height):  # logical height (176)
            for lx in range(self.width):  # logical width (264)
                px, py = logical_to_physical(lx, ly)
                set_physical_pixel(px, py, get_logical_pixel(lx, ly))

        return physical_buffer

    def _rotate_buffer_270_cw(self, logical_buffer):
        """Rotate buffer 270° clockwise (90° counterclockwise) with optimized algorithm"""
        # Physical buffer for actual display dimensions (176x264)
        physical_buffer_size = (EPD_WIDTH * EPD_HEIGHT + 7) // 8
        physical_buffer = bytearray(physical_buffer_size)

        def logical_to_physical(x, y):
            # Rotate 270° clockwise: logical (264w×176h) -> physical (176w×264h)
            # For 270° clockwise: (x,y) -> (height-1-y, x)
            new_x = self.height - 1 - y  # self.height is 176 in landscape mode
            new_y = x
            return new_x, new_y

        def get_logical_pixel(x, y):
            # Get pixel from logical buffer (landscape: 264×176)
            bit_index = y * self.width + x
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            return (logical_buffer[byte_index] >> (7 - bit_offset)) & 1

        def set_physical_pixel(x, y, value):
            # Set pixel in physical buffer (portrait: 176×264)
            bit_index = y * EPD_WIDTH + x
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            if value:
                physical_buffer[byte_index] |= 1 << (7 - bit_offset)
            else:
                physical_buffer[byte_index] &= ~(1 << (7 - bit_offset))

        # Transform from logical coordinates to physical coordinates
        self._log("Transforming coordinates")
        for ly in range(self.height):  # logical height (176)
            for lx in range(self.width):  # logical width (264)
                px, py = logical_to_physical(lx, ly)
                set_physical_pixel(px, py, get_logical_pixel(lx, ly))

        return physical_buffer

    def display(self):
        """Display current frame buffer"""
        self.display_frame(self.buffer)

    def clear(self):
        """Clear display to white using optimized method"""
        self._log("Clearing display")
        self._clear_display_fast()

        # Display update control
        self._command(0x22)
        self._data(0xC7)
        self._command(0x20)  # Master activation
        self.wait_until_idle()

        # Also clear the frame buffer
        self.framebuf.fill(0xFF)

    def fill_black(self):
        """Fill display with black using optimized method"""
        self._log("Filling display with black")

        # Set RAM address counters
        self._command(0x4E)
        self._data(0x00)
        self._command(0x4F)
        self._data(0x00)
        self._data(0x00)

        # Write RAM for black/white
        self._command(0x24)

        # Send all black bytes in batches
        buffer_size = len(self.buffer)
        batch_size = SPI_BATCH_SIZE
        black_data = [0x00] * batch_size

        for i in range(0, buffer_size, batch_size):
            end = min(i + batch_size, buffer_size)
            if end - i == batch_size:
                # Full batch
                self._data_batch(black_data)
            else:
                # Partial batch
                partial_data = [0x00] * (end - i)
                self._data_batch(partial_data)

        # Display update control
        self._command(0x22)
        self._data(0xC7)
        self._command(0x20)  # Master activation
        self.wait_until_idle()

        # Also fill the frame buffer
        self.framebuf.fill(0x00)

    def sleep(self):
        """Put display into deep sleep mode"""
        self._command(DEEP_SLEEP, b"\xA5")

    def reset_display(self):
        """Reset display and clear to white"""
        self._log("Resetting display")

        # Hardware reset
        self.rst(1)
        sleep_ms(200)
        self.rst(0)
        sleep_ms(2)
        self.rst(1)
        sleep_ms(200)

        # Re-initialize
        self.init()

        # Clear to white
        self.clear()

        self._log("Display reset complete")

    def force_clear(self):
        """Force clear to white using optimized method"""
        self._log("Force clearing display")
        self.clear()
        self._log("Force clear complete")

    def clear_large_range(self):
        """Clear to white (same as regular clear)"""
        self._log("Clearing display")
        self.clear()
        self._log("Clear complete")

    # Graphics methods that use the framebuffer
    def fill(self, color):
        """Fill frame buffer with color"""
        self.framebuf.fill(color)

    def text(self, string, x, y, color=0x00):
        """Draw text"""
        self.framebuf.text(string, x, y, color)

    def line(self, x1, y1, x2, y2, color=0x00):
        """Draw line"""
        self.framebuf.line(x1, y1, x2, y2, color)

    def rect(self, x, y, w, h, color=0x00):
        """Draw rectangle"""
        self.framebuf.rect(x, y, w, h, color)

    def fill_rect(self, x, y, w, h, color=0x00):
        """Draw filled rectangle"""
        self.framebuf.fill_rect(x, y, w, h, color)

    def vline(self, x, y, h, color=0x00):
        """Draw vertical line"""
        self.framebuf.vline(x, y, h, color)

    def hline(self, x, y, w, color=0x00):
        """Draw horizontal line"""
        self.framebuf.hline(x, y, w, color)

    def circle(self, x, y, radius, color=0x00):
        """Draw a circle using optimized Bresenham's algorithm"""
        x0, y0 = x, y
        x1, y1 = radius, 0
        err = 0

        while x1 >= y1:
            # Draw 8 symmetric points at once
            self.framebuf.pixel(x0 + x1, y0 + y1, color)
            self.framebuf.pixel(x0 + y1, y0 + x1, color)
            self.framebuf.pixel(x0 - y1, y0 + x1, color)
            self.framebuf.pixel(x0 - x1, y0 + y1, color)
            self.framebuf.pixel(x0 - x1, y0 - y1, color)
            self.framebuf.pixel(x0 - y1, y0 - x1, color)
            self.framebuf.pixel(x0 + y1, y0 - x1, color)
            self.framebuf.pixel(x0 + x1, y0 - y1, color)

            if err <= 0:
                y1 += 1
                err += 2 * y1 + 1
            if err > 0:
                x1 -= 1
                err -= 2 * x1 + 1

    def _load_bmp(self, filename):
        """Load a 1-bit BMP file and return framebuffer data"""
        with open(filename, "rb") as f:
            # Read BMP header (14 bytes)
            header = f.read(14)
            if header[0:2] != b"BM":
                raise ValueError("Not a BMP file")

            # Get offset to pixel data
            pixel_offset = struct.unpack("<I", header[10:14])[0]

            # Read DIB header (40 bytes for BITMAPINFOHEADER)
            dib_header = f.read(40)
            width = struct.unpack("<I", dib_header[4:8])[0]
            height = struct.unpack("<I", dib_header[8:12])[0]
            bits_per_pixel = struct.unpack("<H", dib_header[14:16])[0]

            if bits_per_pixel != 1:
                raise ValueError("Not a 1-bit BMP")

            # Calculate row size (padded to 4 bytes)
            row_size = ((width + 31) // 32) * 4

            # Create framebuffer (MONO_HLSB format)
            fb_width_bytes = (width + 7) // 8
            fb_data = bytearray(fb_width_bytes * height)

            # Seek to pixel data
            f.seek(pixel_offset)

            # Read pixel data (BMP stores bottom-to-top)
            for y in range(height - 1, -1, -1):
                row_data = f.read(row_size)

                # Copy relevant bytes to framebuffer
                for x_byte in range(fb_width_bytes):
                    if x_byte < len(row_data):
                        # BMP is LSB first, framebuffer might need adjustment
                        fb_data[y * fb_width_bytes + x_byte] = row_data[x_byte]

            # Create framebuffer object
            fb = framebuf.FrameBuffer(fb_data, width, height, framebuf.MONO_HLSB)

            return fb, fb_data, width, height

    def draw_bmp(self, filename, x, y):
        """Display a BMP file at the given X/Y coordinates"""
        try:
            # Load the BMP file
            bmp_fb, bmp_data, bmp_width, bmp_height = self._load_bmp(filename)

            # Calculate bounds checking
            if (
                x < 0
                or y < 0
                or x + bmp_width > self.width
                or y + bmp_height > self.height
            ):
                self._log(
                    f"BMP at ({x},{y}) with size {bmp_width}x{bmp_height} would be out of bounds"
                )
                return False

            # Copy BMP pixels to the main framebuffer
            for by in range(bmp_height):
                for bx in range(bmp_width):
                    # Get pixel from BMP framebuffer
                    pixel = bmp_fb.pixel(bx, by)
                    # Set pixel in main framebuffer (invert if needed for your display)
                    self.framebuf.pixel(x + bx, y + by, pixel)

            self._log(f"Displayed BMP {filename} at ({x},{y})")
            return True

        except Exception as e:
            self._log(f"Error displaying BMP {filename}: {e}")
            return False
