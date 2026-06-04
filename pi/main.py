"""
Composite HID: mouse + keyboard, controlled over CDC serial.

Host opens the Pico CDC COM port and sends one command per line:

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

Recovery:
  - Ctrl+C in mpremote interrupts this loop, REPL becomes free.
  - `mpremote touch :.safemode` skips this script on next boot.
  - `mpremote rm :.safemode` re-enables it.
"""
from safemode import SafeMode
from countdown import Countdown
from hid import MouseDevice, KeyboardDevice, HidStack
from key_codes import KeySpecParser
from commands import (
    MoveCommand, ClickCommand, ButtonStateCommand,
    TapKeysCommand, HoldKeysCommand, ReleaseKeysCommand, ReleaseAllKeysCommand,
)
from dispatcher import CommandDispatcher
from serial_reader import SerialReader


def build_dispatcher(mouse, kbd):
    parser = KeySpecParser()
    d = CommandDispatcher()

    d.register("M", MoveCommand(mouse))
    d.register("L", ClickCommand(mouse, "L"))
    d.register("R", ClickCommand(mouse, "R"))
    d.register("X", ClickCommand(mouse, "X"))
    d.register("D", ButtonStateCommand(mouse, down=True))
    d.register("U", ButtonStateCommand(mouse, down=False))

    d.register("K",  TapKeysCommand(kbd, parser))
    d.register("KD", HoldKeysCommand(kbd, parser))
    d.register("KU", ReleaseKeysCommand(kbd, parser))
    d.register("KR", ReleaseAllKeysCommand(kbd))

    return d


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

    mouse = MouseDevice()
    kbd = KeyboardDevice()
    stack = HidStack([mouse, kbd])

    if screen:
        screen.splash("Pico HID", "waiting for host")

    if not stack.attach(timeout_s=5):
        print(">>> host did not open HID, aborting")
        if screen:
            screen.splash("Pico HID", "no host")
        return

    dispatcher = build_dispatcher(mouse, kbd)

    if screen:
        from dashboard import Dashboard
        dispatcher.add_listener(Dashboard(screen))

    try:
        SerialReader(dispatcher).run()
    finally:
        kbd.release_all()


main()
