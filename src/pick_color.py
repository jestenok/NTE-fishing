"""
Пипетка цвета — подбор HSVRange для профилей.

Наведи курсор мыши на нужный цвет в игре и нажми F7. Снимается небольшой
патч вокруг курсора, его цвет переводится в HSV. Можно взять несколько
проб (светлая/тёмная части объекта, край) — итоговый диапазон расширяется,
чтобы покрыть все пробы, и печатается готовой строкой HSVRange(...).

  python pick_color.py

  F7 — взять пробу под курсором
  F9 — выход

Примечание: для красного цвета Hue «кольцевой» (стык 0/180), и диапазон
по min/max выйдет бессмысленно широким. Для циан/зелёного/жёлтого/белого
этой проблемы нет.
"""
import ctypes
import ctypes.wintypes
import time

import cv2
import keyboard
import mss
import numpy as np

from core.io_utils import ensure_utf8_stdout

ensure_utf8_stdout()

_PATCH = 11  # сторона квадрата-пробы, пикселей


def _cursor_pos() -> tuple[int, int]:
    """Абсолютные координаты курсора мыши через WinAPI."""
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def main() -> None:
    sct = mss.MSS()
    mon = sct.monitors[1]
    half = _PATCH // 2
    print(f"Пипетка цвета. Патч {_PATCH}x{_PATCH} px вокруг курсора.")
    print("Наведи на цвет и нажми F7. F9 — выход.")

    lo: np.ndarray | None = None  # накопленный минимум HSV по всем пробам
    hi: np.ndarray | None = None  # накопленный максимум

    def sample() -> None:
        nonlocal lo, hi
        x, y = _cursor_pos()
        left = min(max(x - half, 0), mon["width"] - _PATCH)
        top = min(max(y - half, 0), mon["height"] - _PATCH)
        bbox = {"left": left, "top": top, "width": _PATCH, "height": _PATCH}
        bgr = cv2.cvtColor(np.asarray(sct.grab(bbox)), cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).reshape(-1, 3)
        p_lo = hsv.min(axis=0)
        p_hi = hsv.max(axis=0)
        mean = hsv.mean(axis=0).round().astype(int)
        lo = p_lo if lo is None else np.minimum(lo, p_lo)
        hi = p_hi if hi is None else np.maximum(hi, p_hi)
        rng = [int(v) for v in (*lo, *hi)]
        print(f"\nпроба в ({x}, {y}):")
        print(f"  среднее:  H={mean[0]} S={mean[1]} V={mean[2]}")
        print(f"  в пробе:  H {p_lo[0]}..{p_hi[0]}  "
              f"S {p_lo[1]}..{p_hi[1]}  V {p_lo[2]}..{p_hi[2]}")
        print(f"  по всем пробам → HSVRange({rng[0]}, {rng[1]}, {rng[2]}, "
              f"{rng[3]}, {rng[4]}, {rng[5]})")

    keyboard.add_hotkey("f7", sample)
    while not keyboard.is_pressed("f9"):
        time.sleep(0.05)
    print("\nвыход.")


if __name__ == "__main__":
    main()
