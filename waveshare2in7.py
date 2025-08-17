"""
Fixed MicroPython Waveshare 2.7" Black/White GDEW027W3 e-paper display driver
Based on working implementation from previous tests
"""

from micropython import const
from time import sleep_ms
import framebuf

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


class EPD:
    def __init__(self, spi, cs, dc, rst, busy, orientation=0):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.busy = busy
        self.orientation = orientation

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
        """Send data to display"""
        self.dc(1)
        self.cs(0)
        if isinstance(data, int):
            self.spi.write(bytearray([data]))
        else:
            self.spi.write(data)
        self.cs(1)

    def init(self):
        """Initialize display using corrected sequence"""
        print("Initializing 2.7 inch e-paper display...")

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

    def wait_until_idle(self):
        """Wait until display is not busy"""
        while self.busy.value() == BUSY:
            sleep_ms(100)

    def display_frame(self, frame_buffer):
        """Display frame buffer with proper orientation handling"""
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
        orig_height = EPD_HEIGHT
        orig_bytes_per_row = orig_width // 8

        if self.orientation == 0:
            # Default portrait mode - send data as-is
            for i in range(len(frame_buffer)):
                self._data(frame_buffer[i])

        elif self.orientation == 2:
            # Portrait upside down - reverse byte order and flip bits
            for i in range(len(frame_buffer) - 1, -1, -1):
                # Flip bits in each byte (reverse bit order)
                byte_val = frame_buffer[i]
                flipped_byte = 0
                for bit in range(8):
                    if byte_val & (1 << bit):
                        flipped_byte |= 1 << (7 - bit)
                self._data(flipped_byte)

        elif self.orientation == 1:
            logical_buffer = frame_buffer
            # Physical buffer for actual display dimensions (176x264)
            physical_buffer_size = (EPD_WIDTH * EPD_HEIGHT + 7) // 8
            physical_buffer = bytearray(physical_buffer_size)

            def logical_to_physical(x, y):
                # Rotate 90° clockwise: logical (264w×176h) -> physical (176w×264h)
                # For 90° clockwise: (x,y) -> (y, width-1-x)
                # But we need to map from logical (264×176) to physical (176×264)
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
            print("Transforming from logical coordinates to physical coordinates")
            for ly in range(self.height):  # logical height (176)
                for lx in range(self.width):  # logical width (264)
                    px, py = logical_to_physical(lx, ly)
                    set_physical_pixel(px, py, get_logical_pixel(lx, ly))

            # Send the rotated buffer
            for i in range(len(physical_buffer)):
                self._data(physical_buffer[i])

        elif self.orientation == 3:
            # Landscape left - rotate 90 degrees counter-clockwise
            # Need to transpose the image: swap width/height and rotate data
            new_width = orig_height
            new_height = orig_width
            new_bytes_per_row = new_width // 8

            # Create rotated buffer
            rotated_buffer = bytearray(len(frame_buffer))

            for y in range(orig_height):
                for x in range(orig_width):
                    # Source position in original buffer
                    src_byte_idx = y * orig_bytes_per_row + x // 8
                    src_bit_idx = 7 - (x % 8)  # MONO_HLSB format

                    # Destination position in rotated buffer
                    # Rotate 90° counter-clockwise: (x,y) -> (height-1-y, x)
                    new_x = orig_height - 1 - y
                    new_y = x
                    dst_byte_idx = new_y * new_bytes_per_row + new_x // 8
                    dst_bit_idx = 7 - (new_x % 8)

                    # Copy bit
                    if frame_buffer[src_byte_idx] & (1 << src_bit_idx):
                        rotated_buffer[dst_byte_idx] |= 1 << dst_bit_idx

            # Send rotated data
            for i in range(len(rotated_buffer)):
                self._data(rotated_buffer[i])

        # Display update control
        self._command(0x22)
        self._data(0xC7)
        self._command(0x20)  # Master activation
        self.wait_until_idle()

    def display(self):
        """Display current frame buffer"""
        self.display_frame(self.buffer)

    def clear(self):
        """Clear display to white using working frame buffer method"""
        self.framebuf.fill(0xFF)  # Fill frame buffer with white
        self.display()  # Display the white frame buffer

    def fill_black(self):
        """Fill display with black"""
        self.framebuf.fill(0x00)
        self.display()

    def sleep(self):
        """Put display into deep sleep mode"""
        self._command(DEEP_SLEEP, b"\xA5")

    def reset_display(self):
        """Reset display and clear to white"""
        print("Resetting display...")

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

        print("✓ Display reset complete")

    def force_clear(self):
        """Force clear to white"""
        print("Force clearing display...")
        self.clear()
        print("✓ Force clear complete")

    def clear_large_range(self):
        """Clear to white (same as regular clear)"""
        print("Clearing display...")
        self.clear()
        print("✓ Clear complete")

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
        """Draw a circle"""
        for i in range(-radius, radius + 1):
            for j in range(-radius, radius + 1):
                if i * i + j * j <= radius * radius:
                    self.framebuf.pixel(x + i, y + j, color)
