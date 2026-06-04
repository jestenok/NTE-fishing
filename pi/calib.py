"""Калибровка / верификация GT911 для LCD rotate=270 (480x320).

Рисует крестик в 4 углах физического LCD, ждёт касания, печатает
координату пальца ПОСЛЕ применения swap_xy/invert_y из GT911 defaults.
Если точки совпадают с target ± ~10 px — калибровка корректна.

Скрипт НЕ блокирующий: после 4 касаний завершается, REPL свободен.
"""
from screen import Screen
from touch import GT911
import time


def cross(lcd, x, y, color):
    lcd.fill_rect(x - 10, y - 1, 21, 3, color)
    lcd.fill_rect(x - 1, y - 10, 3, 21, color)


def main():
    t = GT911()  # используем дефолты из touch.py
    s = Screen()

    W = s.width
    HALF = s.half_height
    FULL_H = HALF * 2
    targets = [
        ("TL", 12,        12),
        ("TR", W - 12,    12),
        ("BL", 12,        FULL_H - 12),
        ("BR", W - 12,    FULL_H - 12),
    ]

    print("---- GT911 calibration ----")
    print("screen WxH (full): {}x{}".format(W, FULL_H))

    def wait_release(min_idle_ms=250, timeout_ms=5000):
        """Ждём, пока палец стабильно отпущен на min_idle_ms подряд."""
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        idle_since = None
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            _, _, n = t.read()
            now = time.ticks_ms()
            if n == 0:
                if idle_since is None:
                    idle_since = now
                elif time.ticks_diff(now, idle_since) >= min_idle_ms:
                    return True
            else:
                idle_since = None
            time.sleep_ms(20)
        return False

    def wait_press():
        """Ждём первое валидное касание (палец опущен)."""
        while True:
            rx, ry, n = t.read()
            if n and rx is not None:
                return (rx, ry)
            time.sleep_ms(20)

    results = []
    for name, tx, ty in targets:
        # 1) дождаться чтобы палец был ОТПУЩЕН
        s.status_bottom(["release finger...", "(prepare " + name + ")"], s.RED)
        wait_release()

        # 2) показать крестик в нужной половине экрана
        in_bottom = ty >= HALF
        local_y = ty - HALF if in_bottom else ty

        def render(lcd, lx=tx, ly=local_y, name=name, in_bottom=in_bottom):
            lcd.fill(s.BLACK)
            cross(lcd, lx, ly, s.RED)
            # подпись — на ту же половину, чтобы видеть её
            label_y = HALF - 24 if in_bottom else 4
            lcd.text("tap " + name, 12, label_y, s.WHITE)

        if in_bottom:
            # на верхней — статус, на нижней — крестик
            s.status_top(
                ["target " + name + " ({},{})".format(tx, ty), "TAP NOW"],
                s.GREEN,
            )
            s.draw_bottom(render)
        else:
            s.draw_top(render)
            s.status_bottom(
                ["target " + name + " ({},{})".format(tx, ty), "TAP NOW"],
                s.GREEN,
            )
        rx, ry = wait_press()
        print("{:>2s}: target=({:>3d},{:>3d}) lcd=({:>4d},{:>4d})".format(
            name, tx, ty, rx, ry))
        results.append((name, tx, ty, rx, ry))

    s.splash("calibration", "done — see REPL")
    print("---- summary ----")
    for name, tx, ty, rx, ry in results:
        print("{:>2s} target=({:>3d},{:>3d}) lcd=({:>4d},{:>4d})".format(
            name, tx, ty, rx, ry))
    print("done")


main()
