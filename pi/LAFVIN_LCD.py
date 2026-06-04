"""
Драйвер ILI9488 480x320 для платы LAFVIN Pico Development Kit.
Распиновка по шёлку на плате:
    SCLK=GP2, MOSI=GP3, MISO=GP4, CS=GP5, DC=GP6, RST=GP7
Подсветка запитана от 3V3 напрямую — управлять не надо.
ВНИМАНИЕ: GP13 на этой плате — пьезо-бипер, НЕ трогать как PWM.
"""
from machine import Pin, SPI
import framebuf
import time

LCD_SCK  = 2
LCD_MOSI = 3
LCD_MISO = 4
LCD_CS   = 5
LCD_DC   = 6
LCD_RST  = 7


class LCD_3inch5(framebuf.FrameBuffer):

    def __init__(self):
        # Цветовые константы (BGR565, как в драйвере Waveshare — у их экрана такой порядок)
        self.RED   = 0x07E0
        self.GREEN = 0x001F
        self.BLUE  = 0xF800
        self.WHITE = 0xFFFF
        self.BLACK = 0x0000

        self.rotate = 270  # 0, 90, 180, 270
        if self.rotate in (0, 180):
            self.width  = 320
            self.height = 240
        else:
            self.width  = 480
            self.height = 160

        self.cs  = Pin(LCD_CS,  Pin.OUT, value=1)
        self.dc  = Pin(LCD_DC,  Pin.OUT, value=1)
        self.rst = Pin(LCD_RST, Pin.OUT, value=1)

        self.spi = SPI(0, baudrate=40_000_000,
                       sck=Pin(LCD_SCK),
                       mosi=Pin(LCD_MOSI),
                       miso=Pin(LCD_MISO))

        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()

    def write_cmd(self, cmd):
        self.cs(1); self.dc(0); self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1); self.dc(1); self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        self.rst(1); time.sleep_ms(5)
        self.rst(0); time.sleep_ms(10)
        self.rst(1); time.sleep_ms(5)

        self.write_cmd(0x21)
        self.write_cmd(0xC2); self.write_data(0x33)
        self.write_cmd(0xC5); self.write_data(0x00); self.write_data(0x1E); self.write_data(0x80)
        self.write_cmd(0xB1); self.write_data(0xB0)

        self.write_cmd(0xE0)
        for v in (0x00,0x13,0x18,0x04,0x0F,0x06,0x3A,0x56,0x4D,0x03,0x0A,0x06,0x30,0x3E,0x0F):
            self.write_data(v)

        self.write_cmd(0xE1)
        for v in (0x00,0x13,0x18,0x01,0x11,0x06,0x38,0x34,0x4D,0x06,0x0D,0x0B,0x31,0x37,0x0F):
            self.write_data(v)

        self.write_cmd(0x3A); self.write_data(0x55)
        self.write_cmd(0x11); time.sleep_ms(120)
        self.write_cmd(0x29)
        self.write_cmd(0xB6); self.write_data(0x00); self.write_data(0x62)

        self.write_cmd(0x36)
        if   self.rotate == 0:   self.write_data(0x88)
        elif self.rotate == 180: self.write_data(0x48)
        elif self.rotate == 90:  self.write_data(0xE8)
        else:                    self.write_data(0x28)

    def show_up(self):
        if self.rotate in (0, 180):
            self.write_cmd(0x2A); [self.write_data(v) for v in (0x00,0x00,0x01,0x3F)]
            self.write_cmd(0x2B); [self.write_data(v) for v in (0x00,0x00,0x00,0xEF)]
        else:
            self.write_cmd(0x2A); [self.write_data(v) for v in (0x00,0x00,0x01,0xDF)]
            self.write_cmd(0x2B); [self.write_data(v) for v in (0x00,0x00,0x00,0x9F)]
        self.write_cmd(0x2C)
        self.cs(1); self.dc(1); self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

    def show_down(self):
        if self.rotate in (0, 180):
            self.write_cmd(0x2A); [self.write_data(v) for v in (0x00,0x00,0x01,0x3F)]
            self.write_cmd(0x2B); [self.write_data(v) for v in (0x00,0xF0,0x01,0xDF)]
        else:
            self.write_cmd(0x2A); [self.write_data(v) for v in (0x00,0x00,0x01,0xDF)]
            self.write_cmd(0x2B); [self.write_data(v) for v in (0x00,0xA0,0x01,0x3F)]
        self.write_cmd(0x2C)
        self.cs(1); self.dc(1); self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)
