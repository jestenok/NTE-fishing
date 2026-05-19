"""
Утилита калибровки слайдер-механики выбранного профиля.

Режимы:
  python calibrate.py screen [--delay N]   — захват экрана через N сек (по умолч. 5).
                                              Пока тикает отсчёт — Alt+Tab в игру.
  python calibrate.py file <path> [--full] — прогон детектора на готовом скриншоте.
                                              --full = картинка уже вырезанная полоса.

Опции:
  --profile <имя>   — какой профиль брать (по умолчанию settings.ACTIVE_PROFILE).

Сохраняет в images/:
  debug_input.png     — что попало в детектор
  debug_zone.png      — маска зоны-цели
  debug_slider.png    — маска ползунка
  debug_overlay.png   — исходник с разметкой найденного
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from core.capture import ScreenCapture
from core.hsv import mask_one
from core.io_utils import ensure_utf8_stdout
from mechanics.slider import BarDetector, SliderConfig, annotate
from profiles.base import GameProfile, load_profile
from settings import ACTIVE_PROFILE

ensure_utf8_stdout()


def _find_slider(profile: GameProfile) -> SliderConfig:
    for module in profile.modules:
        if isinstance(module, SliderConfig):
            return module
    sys.exit(f"в профиле '{profile.name}' нет слайдер-механики")


def _save(name: str, img: np.ndarray) -> None:
    Path("images").mkdir(exist_ok=True)
    cv2.imwrite(name, img)
    print(f"  saved {name}  ({img.shape[1]}x{img.shape[0]})")


def _process(img_bgr: np.ndarray, slider: SliderConfig) -> None:
    det = BarDetector(slider).detect(img_bgr)
    print(f"zone:   x1={det.zone_x1} x2={det.zone_x2} center={det.zone_center}")
    print(f"slider: x={det.slider_x}")
    if det.has_zone and det.has_slider:
        err = det.slider_x - det.zone_center
        key_a = slider.key_right if slider.invert_keys else slider.key_left
        key_d = slider.key_left if slider.invert_keys else slider.key_right
        print(f"err:    {err:+d} px (>0 → нажать {key_a.upper()}, "
              f"<0 → нажать {key_d.upper()})")
    _save("images/debug_input.png", img_bgr)
    _save("images/debug_zone.png", mask_one(img_bgr, slider.zone_hsv))
    _save("images/debug_slider.png", mask_one(img_bgr, slider.slider_hsv))
    _save("images/debug_overlay.png", annotate(img_bgr, det))


def _countdown(seconds: float) -> None:
    if seconds <= 0:
        return
    print(f"Переключайся в игру и открой рыбалку. Снимок через {seconds:.0f} сек:")
    for i in range(int(seconds), 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)


def _from_screen(slider: SliderConfig, delay: float) -> None:
    cap = ScreenCapture(slider.region)
    print(f"screen: {cap.screen_w}x{cap.screen_h}")
    print(f"region: {cap.bbox}")
    _countdown(delay)
    _process(cap.grab(), slider)


def _from_file(slider: SliderConfig, path: str, full: bool) -> None:
    p = Path(path)
    if not p.exists():
        sys.exit(f"file not found: {p}")
    img = cv2.imread(str(p))
    if img is None:
        sys.exit(f"cannot read image: {p}")
    h, w = img.shape[:2]
    print(f"file: {p}  ({w}x{h})")
    if full:
        _process(img, slider)
        return
    rx, ry, rw, rh = slider.region.to_pixels(w, h)
    print(f"crop region: x={rx} y={ry} w={rw} h={rh}")
    _process(img[ry:ry + rh, rx:rx + rw], slider)


def _parse_delay(args: list[str]) -> float:
    if "--delay" not in args:
        return 5.0
    i = args.index("--delay")
    if i + 1 >= len(args):
        sys.exit("--delay expects a number")
    return float(args[i + 1])


def main() -> None:
    args = sys.argv[1:]

    profile_name = ACTIVE_PROFILE
    if "--profile" in args:
        i = args.index("--profile")
        if i + 1 >= len(args):
            sys.exit("--profile expects a name")
        profile_name = args[i + 1]
        del args[i:i + 2]

    profile = load_profile(profile_name)
    slider = _find_slider(profile)

    if not args:
        print(__doc__)
        return
    mode = args[0]
    if mode == "screen":
        _from_screen(slider, _parse_delay(args[1:]))
    elif mode == "file":
        if len(args) < 2:
            sys.exit("usage: python calibrate.py file <path> [--full]")
        _from_file(slider, args[1], "--full" in args[2:])
    else:
        sys.exit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
