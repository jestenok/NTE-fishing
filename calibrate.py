"""
Утилита калибровки.

Режимы:
  python calibrate.py screen [--delay N]   — захват экрана через N сек (по умолч. 5).
                                              Пока тикает обратный отсчёт — Alt+Tab в игру.
  python calibrate.py file <path> [--full] — прогон детектора на готовом скриншоте.
                                              --full = обработать как уже вырезанную полосу.

Сохраняет:
  debug_input.png     — что попало в детектор
  debug_zone.png      — маска циан-зоны
  debug_slider.png    — маска ползунка
  debug_overlay.png   — исходник с разметкой найденного
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from config import CONFIG, HSVRange
from io_utils import ensure_utf8_stdout
from vision import BarDetector, ScreenCapture, annotate

ensure_utf8_stdout()


def _save(name: str, img: np.ndarray) -> None:
    cv2.imwrite(name, img)
    print(f"  saved {name}  ({img.shape[1]}x{img.shape[0]})")


def _mask(img_bgr: np.ndarray, rng: HSVRange) -> np.ndarray:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(rng.lower()), np.array(rng.upper()))


def _process(img_bgr: np.ndarray) -> None:
    det = BarDetector().detect(img_bgr)
    print(f"zone:   x1={det.zone_x1} x2={det.zone_x2} center={det.zone_center}")
    print(f"slider: x={det.slider_x}")
    if det.has_zone and det.has_slider:
        err = det.slider_x - det.zone_center
        print(f"err:    {err:+d} px (>0 → нажать A, <0 → нажать D)")
    _save("debug_input.png", img_bgr)
    _save("debug_zone.png", _mask(img_bgr, CONFIG.zone_hsv))
    _save("debug_slider.png", _mask(img_bgr, CONFIG.slider_hsv))
    _save("debug_overlay.png", annotate(img_bgr, det))


def _countdown(seconds: float) -> None:
    if seconds <= 0:
        return
    print(f"Переключайся в игру и открой рыбалку. Снимок через {seconds:.0f} сек:")
    for i in range(int(seconds), 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)


def _from_screen(delay: float) -> None:
    cap = ScreenCapture()
    print(f"screen: {cap.screen_w}x{cap.screen_h}")
    print(f"region: {cap.bbox}")
    _countdown(delay)
    _process(cap.grab())


def _from_file(path: str, full: bool) -> None:
    p = Path(path)
    if not p.exists():
        sys.exit(f"file not found: {p}")
    img = cv2.imread(str(p))
    if img is None:
        sys.exit(f"cannot read image: {p}")
    h, w = img.shape[:2]
    print(f"file: {p}  ({w}x{h})")
    if full:
        _process(img)
        return
    rx, ry, rw, rh = CONFIG.region.to_pixels(w, h)
    print(f"crop region: x={rx} y={ry} w={rw} h={rh}")
    _process(img[ry:ry + rh, rx:rx + rw])


def _parse_delay(args: list[str]) -> float:
    if "--delay" not in args:
        return 5.0
    i = args.index("--delay")
    if i + 1 >= len(args):
        sys.exit("--delay expects a number")
    return float(args[i + 1])


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    mode = args[0]
    if mode == "screen":
        _from_screen(_parse_delay(args[1:]))
    elif mode == "file":
        if len(args) < 2:
            sys.exit("usage: python calibrate.py file <path> [--full]")
        _from_file(args[1], "--full" in args[2:])
    else:
        sys.exit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
