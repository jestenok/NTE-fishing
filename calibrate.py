"""
Утилита калибровки.

Режимы:
  python calibrate.py screen [--delay N]   — захват с экрана через N секунд (по умолчанию 5).
                                              Пока идёт обратный отсчёт — Alt+Tab в игру и открой рыбалку.
  python calibrate.py file <path>          — прогон детектора на готовом скриншоте.

Сохраняет:
  debug_input.png   — то, что попало в детектор
  debug_zone.png    — маска зелёной зоны
  debug_slider.png  — маска ползунка
  debug_overlay.png — исходник с разметкой
"""
import io
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
elif isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import cv2
import numpy as np

from config import CONFIG
from vision import Grabber, _mask, annotate, detect


def _save(name: str, img: np.ndarray):
    cv2.imwrite(name, img)
    print(f"  saved {name}  ({img.shape[1]}x{img.shape[0]})")


def _process(img_bgr: np.ndarray):
    det = detect(img_bgr)
    print(f"zone:   x1={det.zone_x1} x2={det.zone_x2} center={det.zone_center}")
    print(f"slider: x={det.slider_x}")
    if det.has_zone and det.has_slider:
        err = det.slider_x - det.zone_center
        print(f"err:    {err:+d} px (>0 → нажать A, <0 → нажать D)")

    _save("debug_input.png", img_bgr)
    _save("debug_zone.png", _mask(img_bgr, CONFIG.zone_hsv))
    _save("debug_slider.png", _mask(img_bgr, CONFIG.slider_hsv))
    _save("debug_overlay.png", annotate(img_bgr, det))


def _from_screen(delay: float):
    g = Grabber()
    print(f"screen: {g.screen_w}x{g.screen_h}")
    print(f"region: {g._bbox}")
    if delay > 0:
        print(f"Переключайся в игру и открой рыбалку. Снимок через {delay:.0f} сек:")
        for i in range(int(delay), 0, -1):
            print(f"  {i}...", flush=True)
            time.sleep(1)
    _process(g.grab())


def _from_file(path: str, full: bool):
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
    crop = img[ry:ry + rh, rx:rx + rw]
    _process(crop)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    mode = args[0]
    if mode == "screen":
        delay = 5.0
        for i, a in enumerate(args[1:]):
            if a == "--delay" and i + 2 < len(args):
                delay = float(args[i + 2])
        _from_screen(delay)
    elif mode == "file":
        if len(args) < 2:
            sys.exit("usage: python calibrate.py file <path> [--full]")
        full = "--full" in args[2:]
        _from_file(args[1], full)
    else:
        sys.exit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
