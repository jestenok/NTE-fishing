"""
Измеритель региона экрана для config.Region.

Зайди в игру, открой нужный элемент (полосу рыбалки и т.п.), затем:
  1. наведи курсор мыши на ЛЕВЫЙ-ВЕРХНИЙ угол области → нажми F7
  2. наведи курсор на ПРАВЫЙ-НИЖНИЙ угол → нажми F7

Скрипт печатает готовые значения x1/y1/x2/y2 в долях экрана (0.0–1.0),
которые можно вставить прямо в Region в config.py.

  python measure.py

  F7 — зафиксировать точку под курсором
  F9 — выход
"""
import ctypes
import ctypes.wintypes
import time

import keyboard
import mss

from core.io_utils import ensure_utf8_stdout

ensure_utf8_stdout()


def _cursor_pos() -> tuple[int, int]:
    """Абсолютные координаты курсора мыши через WinAPI."""
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def main() -> None:
    sct = mss.MSS()
    mon = sct.monitors[1]
    screen_w, screen_h = mon["width"], mon["height"]
    mon_left, mon_top = mon["left"], mon["top"]
    print(f"screen: {screen_w}x{screen_h}")
    print("Наведи курсор на ЛЕВЫЙ-ВЕРХНИЙ угол области и нажми F7.")
    print("F9 — выход.")

    points: list[tuple[float, float]] = []

    def capture() -> None:
        x, y = _cursor_pos()
        fx = (x - mon_left) / screen_w
        fy = (y - mon_top) / screen_h
        points.append((fx, fy))
        corner = "левый-верхний" if len(points) == 1 else "правый-нижний"
        print(f"  точка {len(points)} ({corner}): "
              f"pixel=({x}, {y})  доля=({fx:.3f}, {fy:.3f})")
        if len(points) == 1:
            print("Теперь наведи на ПРАВЫЙ-НИЖНИЙ угол и нажми F7.")

    keyboard.add_hotkey("f7", capture)

    while len(points) < 2:
        if keyboard.is_pressed("f9"):
            print("Отмена.")
            return
        time.sleep(0.05)

    (ax, ay), (bx, by) = points
    x1, x2 = sorted((ax, bx))
    y1, y2 = sorted((ay, by))
    print()
    print("Готовая область для config.Region:")
    print(f"    x1: float = {x1:.3f}")
    print(f"    y1: float = {y1:.3f}")
    print(f"    x2: float = {x2:.3f}")
    print(f"    y2: float = {y2:.3f}")
    print()
    print(f"  → Region(x1={x1:.3f}, y1={y1:.3f}, x2={x2:.3f}, y2={y2:.3f})")


if __name__ == "__main__":
    main()
