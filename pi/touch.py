"""GT911 ёмкостный тач (адрес 0x5D) на шине I²C0 GP8/9, RST=GP10, INT=GP11.

Координаты GT911 нативно отдаются в системе панели; класс умеет применять
swap_xy/invert_x/invert_y, чтобы соответствовать ориентации LCD (rotate=270).
"""
from machine import Pin, I2C
import time

_REG_STATUS = 0x814E
_REG_TOUCH0 = 0x8150  # X_LO, X_HI, Y_LO, Y_HI, SIZE_LO, SIZE_HI, RESERVED
_REG_CONFIG_VER = 0x8047


class GT911:
    def __init__(self, i2c=None, addr=0x5D, rst_pin=10, int_pin=11,
                 width=480, height=320,
                 swap_xy=True, invert_x=False, invert_y=True):
        self._addr = addr
        self._map = self._build_mapper(swap_xy, invert_x, invert_y, width, height)

        self._rst = Pin(rst_pin, Pin.OUT, value=0)
        self._int = Pin(int_pin, Pin.OUT, value=0)
        self._reset_sequence()
        # После reset INT снова на вход чтобы не мешать
        self._int = Pin(int_pin, Pin.IN)

        if i2c is None:
            i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
        self._i2c = i2c

    def _reset_sequence(self):
        # Адрес 0x5D: INT держим в 0 при отпускании RST.
        self._int.value(0)
        self._rst.value(0)
        time.sleep_ms(10)
        self._rst.value(1)
        time.sleep_ms(10)
        # После этого INT становится входом (см. __init__)
        time.sleep_ms(50)

    def _read(self, reg, n):
        return self._i2c.readfrom_mem(self._addr, reg, n, addrsize=16)

    def _write(self, reg, data):
        self._i2c.writeto_mem(self._addr, reg, data, addrsize=16)

    def read(self):
        """Возвращает (x, y, n_touches) или (None, None, 0)."""
        st = self._read(_REG_STATUS, 1)[0]
        if not (st & 0x80):
            return (None, None, 0)
        n = st & 0x0F
        if n == 0:
            self._write(_REG_STATUS, b"\x00")
            return (None, None, 0)
        buf = self._read(_REG_TOUCH0, 7)
        self._write(_REG_STATUS, b"\x00")
        rx = buf[0] | (buf[1] << 8)
        ry = buf[2] | (buf[3] << 8)
        return self._map(rx, ry) + (n,)

    @staticmethod
    def _build_mapper(swap, invx, invy, w, h):
        fx = (lambda v: w - 1 - v) if invx else (lambda v: v)
        fy = (lambda v: h - 1 - v) if invy else (lambda v: v)
        if swap:
            return lambda rx, ry: (fx(ry), fy(rx))
        return lambda rx, ry: (fx(rx), fy(ry))
