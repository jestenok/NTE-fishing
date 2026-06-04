import time
import usb.device
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
