"""
Composite HID: mouse + keyboard + vendor raw-HID control channel.

Хост открывает vendor HID интерфейс и слаёт OUT-репортами по одной команде:

  MOUSE
    M <dx> <dy>      relative move (signed int8 each, -127..127)
    L                left click
    R                right click
    X                middle click
    D <L|R|X>        mouse button DOWN (hold)
    U <L|R|X>        mouse button UP (release)

  KEYBOARD
    K <spec>         tap key/combo:  K A   |   K SPACE   |   K CTRL+C   |   K SHIFT+F4
    KD <spec>        key DOWN (added to held set, stays until released)
    KU <spec>        key UP (removed from held set)
    KR               release ALL keys

  spec is one or more names joined by '+', e.g. CTRL+SHIFT+A.
  Modifiers: CTRL/LCTRL/RCTRL, SHIFT/LSHIFT/RSHIFT, ALT/LALT/RALT, WIN/GUI/LGUI/RGUI.
  Letters: A..Z. Digits: 0..9 (or N0..N9). Others: SPACE, ENTER, TAB, ESCAPE, BACKSPACE,
  DELETE, F1..F12, UP, DOWN, LEFT, RIGHT, HOME, END, PGUP, PGDN, etc.

Тач-кнопки шлют IN-репорты `CTL RUN|PROF_NEXT|DBG_NEXT|QUIT` обратно хосту.

Recovery:
  - Ctrl+C в REPL прерывает этот цикл.
  - `mpremote touch :.safemode` пропускает скрипт на следующий boot.
  - `mpremote rm :.safemode` снова включает.
"""
from safemode import SafeMode
from countdown import Countdown
from key_codes import KeySpecParser
from commands import (
    MoveCommand, ClickCommand, ButtonStateCommand,
    TapKeysCommand, HoldKeysCommand, ReleaseKeysCommand, ReleaseAllKeysCommand,
    NoopCommand, CallbackCommand,
)
from dispatcher import CommandDispatcher
from hid_reader import HidReader


def build_dispatcher(mouse, kbd, status_callback=None):
    parser = KeySpecParser()
    d = CommandDispatcher()

    if mouse:
        d.register("M", MoveCommand(mouse))
        d.register("L", ClickCommand(mouse, "L"))
        d.register("R", ClickCommand(mouse, "R"))
        d.register("X", ClickCommand(mouse, "X"))
        d.register("D", ButtonStateCommand(mouse, down=True))
        d.register("U", ButtonStateCommand(mouse, down=False))

    if kbd:
        d.register("K",  TapKeysCommand(kbd, parser))
        d.register("KD", HoldKeysCommand(kbd, parser))
        d.register("KU", ReleaseKeysCommand(kbd, parser))
        d.register("KR", ReleaseAllKeysCommand(kbd))

    d.register("CTL", NoopCommand())  # тач-кнопки эмитят CTL <cmd>

    if status_callback:
        d.register("STATUS", CallbackCommand(status_callback))
    else:
        d.register("STATUS", NoopCommand())

    return d


def try_init_hid(screen):
    """Возвращает (mouse, kbd, vendor) или (None, None, None) если HID-стек недоступен."""
    try:
        from hid import MouseDevice, KeyboardDevice, VendorHidDevice, HidStack
    except ImportError as e:
        print("HID lib unavailable:", e)
        if screen:
            screen.splash("Pico HID", "no usb.device lib")
        return (None, None, None)

    mouse = MouseDevice()
    kbd = KeyboardDevice()
    vendor = VendorHidDevice()
    stack = HidStack([mouse, kbd, vendor])
    if screen:
        screen.splash("Pico HID", "waiting for host")
    if not stack.attach(timeout_s=5):
        print(">>> host did not open HID")
        if screen:
            screen.splash("Pico HID", "no host (HID off)")
        return (None, None, None)
    return (mouse, kbd, vendor)


def try_get_touch():
    try:
        from touch import GT911
        return GT911()
    except Exception as e:
        print("touch unavailable:", e)
        return None


def try_get_beeper():
    try:
        from beeper import Beeper
        return Beeper()
    except Exception as e:
        print("beeper unavailable:", e)
        return None


def try_get_screen():
    try:
        from screen import Screen
        return Screen()
    except Exception as e:
        print("screen unavailable:", e)
        return None


def main():
    if SafeMode().is_active():
        print(">>> safemode: HID init skipped")
        return

    screen = try_get_screen()
    if screen:
        screen.splash("Pico HID", "countdown 5s")

    if not Countdown(5).wait():
        if screen:
            screen.splash("Pico HID", "aborted")
        return

    mouse, kbd, vendor = try_init_hid(screen)
    beeper = try_get_beeper()

    dashboard = None
    if screen:
        from dashboard import Dashboard
        dashboard = Dashboard(screen, beeper=beeper)

    status_cb = dashboard.set_status if dashboard else None
    dispatcher = build_dispatcher(mouse, kbd, status_callback=status_cb)

    if dashboard:
        dispatcher.add_listener(dashboard)

    if vendor is None:
        print(">>> no vendor HID, idle loop")
        return

    reader = HidReader(vendor, dispatcher)
    if beeper:
        reader.add_ticker(beeper.tick)

    if screen:
        touch = try_get_touch()
        if touch:
            from touch_panel import TouchPanel
            panel = TouchPanel(screen, touch, dispatcher, vendor_hid=vendor)
            reader.add_ticker(panel.poll)

    try:
        reader.run()
    finally:
        if kbd:
            kbd.release_all()


main()
