import time
import usb.device
from usb.device.hid import HIDInterface
from usb.device.mouse import MouseInterface
from usb.device.keyboard import KeyboardInterface


class HidDevice:
    def is_open(self):
        raise NotImplementedError

    @property
    def iface(self):
        raise NotImplementedError


class Pointer:
    def move(self, dx, dy):
        raise NotImplementedError


class Clicker:
    def press(self, button):
        raise NotImplementedError

    def release(self, button):
        raise NotImplementedError

    def click(self, button):
        self.press(button)
        self.release(button)


class Typist:
    def tap(self, codes):
        raise NotImplementedError

    def hold(self, codes):
        raise NotImplementedError

    def release_keys(self, codes):
        raise NotImplementedError

    def release_all(self):
        raise NotImplementedError


_VENDOR_IFACE_STR = "USB HID"


class MouseDevice(HidDevice, Pointer, Clicker):
    def __init__(self, iface=None):
        self._iface = iface or MouseInterface()

    @property
    def iface(self):
        return self._iface

    def is_open(self):
        return self._iface.is_open()

    def move(self, dx, dy):
        self._iface.move_by(dx, dy)

    def press(self, button):
        self._set_button(button, True)

    def release(self, button):
        self._set_button(button, False)

    def _set_button(self, button, down):
        b = button.upper()
        if b == "L":
            self._iface.click_left(down)
        elif b == "R":
            self._iface.click_right(down)
        elif b == "X":
            self._iface.click_middle(down)
        else:
            raise ValueError("unknown button: " + button)


class KeyboardDevice(HidDevice, Typist):
    def __init__(self, iface=None):
        self._iface = iface or KeyboardInterface()
        self._held = set()

    @property
    def iface(self):
        return self._iface

    def is_open(self):
        return self._iface.is_open()

    def tap(self, codes):
        combo = list(self._held) + list(codes)
        self._iface.send_keys(combo)
        self._iface.send_keys(list(self._held))

    def hold(self, codes):
        for c in codes:
            self._held.add(c)
        self._iface.send_keys(list(self._held))

    def release_keys(self, codes):
        for c in codes:
            self._held.discard(c)
        self._iface.send_keys(list(self._held))

    def release_all(self):
        self._held.clear()
        self._iface.send_keys([])


_VENDOR_REPORT_DESCRIPTOR = bytes((
    0x06, 0x00, 0xFF,  # Usage Page (Vendor Defined 0xFF00)
    0x09, 0x01,        # Usage 0x01
    0xA1, 0x01,        # Collection (Application)
    0x09, 0x02,        #   Usage 0x02 (IN data)
    0x15, 0x00,        #   Logical Minimum 0
    0x26, 0xFF, 0x00,  #   Logical Maximum 255
    0x75, 0x08,        #   Report Size 8
    0x95, 0x40,        #   Report Count 64
    0x81, 0x02,        #   Input (Data, Var, Abs)
    0x09, 0x03,        #   Usage 0x03 (OUT data)
    0x91, 0x02,        #   Output (Data, Var, Abs)
    0xC0,              # End Collection
))


class _VendorIface(HIDInterface):
    """Raw HID 64-байтный канал. OUT-репорты от хоста складываются в очередь."""

    def __init__(self):
        super().__init__(
            _VENDOR_REPORT_DESCRIPTOR,
            set_report_buf=bytearray(64),
            protocol=0,
            interface_str=_VENDOR_IFACE_STR,
        )
        self._rx = []

    def on_set_report(self, report_data, report_id):
        # report_data — memoryview в set_report_buf, фиксируем срез.
        self._rx.append(bytes(report_data))

    def pop_rx(self):
        if not self._rx:
            return None
        return self._rx.pop(0)


class VendorHidDevice(HidDevice):
    """Двусторонний 64-байт raw HID канал host<->pico.

    Формат репорта (IN и OUT одинаково): [len:1][payload:63].
    `payload` — ASCII команда, остаток нулями. На хосте hidapi пишет
    OUT-репорт через SET_REPORT (контрол), нам этого хватает.
    """

    def __init__(self, iface=None):
        self._iface = iface or _VendorIface()

    @property
    def iface(self):
        return self._iface

    def is_open(self):
        return self._iface.is_open()

    def send(self, line):
        """Шлёт текстовую строку IN-репортом. Не блокирует — при ошибке молча скипает."""
        if isinstance(line, str):
            payload = line.encode("utf-8", "replace")
        else:
            payload = bytes(line)
        n = len(payload)
        if n > 63:
            payload = payload[:63]
            n = 63
        report = bytearray(64)
        report[0] = n
        report[1:1 + n] = payload
        try:
            self._iface.send_report(report)
        except Exception:
            pass

    def recv(self):
        """Достаёт следующий принятый OUT-репорт как str или None."""
        chunk = self._iface.pop_rx()
        if not chunk:
            return None
        n = chunk[0]
        if n == 0 or n > 63:
            return None
        return chunk[1:1 + n].decode("utf-8", "replace")


class HidStack:
    """Композитная USB-инициализация для набора HID-устройств."""

    def __init__(self, devices):
        self._devices = list(devices)

    def attach(self, timeout_s=5):
        usb.device.get().init(
            *[d.iface for d in self._devices],
            builtin_driver=True,
        )
        deadline = time.ticks_add(time.ticks_ms(), int(timeout_s * 1000))
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self.is_open():
                return True
            time.sleep_ms(50)
        return self.is_open()

    def is_open(self):
        return all(d.is_open() for d in self._devices)
