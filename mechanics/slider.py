"""Механика «полоса с зоной и ползунком».

На экране горизонтальная полоса: цветная зона-цель и маркер-ползунок.
Задача — удерживать ползунок в центре зоны, нажимая две клавиши.
Это классическая мини-игра рыбалки/ковки/взлома во многих играх.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from core.capture import ScreenCapture
from core.controller import KeyHolder
from core.geometry import Region
from core.humanizer import LEFT, RIGHT, Humanizer, HumanizerConfig
from core.hsv import HSVRange

_MAX_GAP_PX = 15


@dataclass(frozen=True, slots=True)
class Detection:
    zone_x1: int | None
    zone_x2: int | None
    slider_x: int | None

    @property
    def has_zone(self) -> bool:
        return self.zone_x1 is not None and self.zone_x2 is not None

    @property
    def has_slider(self) -> bool:
        return self.slider_x is not None

    @property
    def zone_center(self) -> int | None:
        if self.zone_x1 is None or self.zone_x2 is None:
            return None
        return (self.zone_x1 + self.zone_x2) // 2


@dataclass
class SliderConfig:
    """Параметры слайдер-механики для одной игры."""
    region: Region
    zone_hsv: HSVRange
    slider_hsv: HSVRange

    key_left: str = "a"
    key_right: str = "d"
    invert_keys: bool = False  # переключить, если бот тянет в обратную сторону

    deadband_px: int = 4          # внутри ±этого — отпустить клавиши
    engage_threshold_px: int = 9  # снова нажимать только если ушло за ±этого (гистерезис)

    slider_search_margin_px: int = 8
    min_zone_width_px: int = 8
    min_slider_area_px: int = 2

    humanizer: HumanizerConfig = field(default_factory=HumanizerConfig)

    name: str = "slider"
    debug: bool = False  # подробный лог каждого кадра

    def build(self) -> "SliderMechanic":
        return SliderMechanic(self)


class BarDetector:
    """Поиск цветной зоны и маркера-ползунка на полосе.

    HSV-маски считаются с переиспользуемыми буферами через `dst=` параметр cv2,
    чтобы не аллоцировать ndarray каждый кадр.
    """

    def __init__(self, cfg: SliderConfig) -> None:
        self.cfg = cfg
        self._zone_lo = cfg.zone_hsv.lo_array()
        self._zone_hi = cfg.zone_hsv.hi_array()
        self._slider_lo = cfg.slider_hsv.lo_array()
        self._slider_hi = cfg.slider_hsv.hi_array()
        self._hsv: np.ndarray | None = None
        self._zone_mask: np.ndarray | None = None
        self._slider_mask: np.ndarray | None = None

    def detect(self, img_bgr: np.ndarray) -> Detection:
        self._hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV, dst=self._hsv)
        self._zone_mask = cv2.inRange(self._hsv, self._zone_lo, self._zone_hi, dst=self._zone_mask)
        self._slider_mask = cv2.inRange(self._hsv, self._slider_lo, self._slider_hi, dst=self._slider_mask)

        zone_run = _largest_run(self._zone_mask, self.cfg.min_zone_width_px)
        if zone_run is None:
            slider_x = _centroid_x(self._slider_mask, self.cfg.min_slider_area_px)
            return Detection(None, None, slider_x)

        slider_x = _centroid_x_in_window(
            self._slider_mask, zone_run, self.cfg.slider_search_margin_px,
            self.cfg.min_slider_area_px,
        )
        if slider_x is None:
            slider_x = _centroid_x(self._slider_mask, self.cfg.min_slider_area_px)
        return Detection(zone_run[0], zone_run[1], slider_x)


def _largest_run(mask: np.ndarray, min_width: int) -> tuple[int, int] | None:
    """Самый длинный «прогон» активных колонок в маске, склеивая соседей < MAX_GAP."""
    col_hits = (mask > 0).sum(axis=0)
    active = col_hits >= 2
    if not active.any():
        return None

    idx = np.flatnonzero(active)
    gaps = np.diff(idx) > _MAX_GAP_PX
    splits = np.flatnonzero(gaps) + 1

    starts = idx[np.r_[0, splits]]
    ends = idx[np.r_[splits - 1, len(idx) - 1]] + 1
    widths = ends - starts

    valid = widths >= min_width
    if not valid.any():
        return None
    valid_w = widths[valid]
    best = int(valid_w.argmax())
    valid_idx = np.flatnonzero(valid)[best]
    return int(starts[valid_idx]), int(ends[valid_idx])


def _centroid_x(mask: np.ndarray, min_area: int) -> int | None:
    xs = np.flatnonzero(mask.any(axis=0))
    if xs.size < min_area:
        return None
    # area-weighted centroid: sum of column hits as weight
    col_hits = (mask > 0).sum(axis=0)
    total = col_hits.sum()
    if total < min_area:
        return None
    return int((np.arange(mask.shape[1]) * col_hits).sum() / total)


def _centroid_x_in_window(
    mask: np.ndarray,
    zone_run: tuple[int, int],
    margin: int,
    min_area: int,
) -> int | None:
    x_lo = max(0, zone_run[0] - margin)
    x_hi = min(mask.shape[1], zone_run[1] + margin)
    sub = mask[:, x_lo:x_hi]
    cx = _centroid_x(sub, min_area)
    return cx + x_lo if cx is not None else None


def annotate(img_bgr: np.ndarray, det: Detection) -> np.ndarray:
    """Рисует найденные зону и ползунок поверх кадра. Используется в calibrate."""
    out = img_bgr.copy()
    h = out.shape[0]
    if det.has_zone:
        cv2.rectangle(out, (det.zone_x1, 0), (det.zone_x2, h - 1), (0, 255, 0), 1)
        cv2.line(out, (det.zone_center, 0), (det.zone_center, h - 1), (0, 200, 0), 1)
    if det.has_slider:
        cv2.line(out, (det.slider_x, 0), (det.slider_x, h - 1), (0, 0, 255), 1)
    return out


class SliderMechanic:
    """Модуль бота: захват полосы → детект → humanizer → нажатие клавиш."""

    def __init__(self, cfg: SliderConfig) -> None:
        self.cfg = cfg
        self.name = cfg.name
        self._cap = ScreenCapture(cfg.region)
        self._detector = BarDetector(cfg)
        self._humanizer = Humanizer(cfg.humanizer)
        self._keys = self._build_keys(cfg)
        self._log_interval = 0.1 if cfg.debug else 0.5
        self._last_log = 0.0
        self._last_frame: np.ndarray | None = None
        self._last_det: Detection | None = None

    @staticmethod
    def _build_keys(cfg: SliderConfig) -> KeyHolder:
        if cfg.invert_keys:
            return KeyHolder(cfg.key_right, cfg.key_left)
        return KeyHolder(cfg.key_left, cfg.key_right)

    def tick(self, now: float) -> str | None:
        frame = self._cap.grab()
        det = self._detector.detect(frame)
        self._last_frame = frame
        self._last_det = det
        slider_x = float(det.slider_x) if det.has_slider else None
        zone_center = float(det.zone_center) if det.has_zone else None
        action = self._humanizer.step(
            slider_x, zone_center,
            self.cfg.deadband_px, self.cfg.engage_threshold_px,
        )
        self._apply(action)
        return self._log(now, det, action)

    def _apply(self, action: str) -> None:
        if action == LEFT:
            self._keys.press_left()
        elif action == RIGHT:
            self._keys.press_right()
        else:
            self._keys.release_all()

    def _log(self, now: float, det: Detection, action: str) -> str | None:
        if now - self._last_log < self._log_interval:
            return None
        self._last_log = now
        zc = det.zone_center if det.has_zone else None
        sx = det.slider_x if det.has_slider else None
        err = (sx - zc) if (sx is not None and zc is not None) else None
        sx_s = f"{sx:>4}" if sx is not None else "  — "
        zc_s = f"{zc:>4}" if zc is not None else "  — "
        err_s = f"{err:+4d}" if err is not None else "  — "
        return (f"[{self._keys.state}] slider={sx_s} zone_c={zc_s} "
                f"err={err_s} action={action}")

    def debug_panel(self) -> tuple[np.ndarray, bool] | None:
        if self._last_frame is None or self._last_det is None:
            return None
        img = annotate(self._last_frame, self._last_det)
        detected = self._last_det.has_zone and self._last_det.has_slider
        return img, detected

    def on_stop(self) -> None:
        self._keys.release_all()
        self._humanizer.reset()
