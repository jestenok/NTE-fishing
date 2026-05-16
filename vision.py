from dataclasses import dataclass

import cv2
import mss
import numpy as np

from config import CONFIG, HSVRange

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


class ScreenCapture:
    """Захват прямоугольной области экрана через mss."""

    def __init__(self) -> None:
        self._sct = mss.MSS()
        monitor = self._sct.monitors[1]
        self.screen_w: int = monitor["width"]
        self.screen_h: int = monitor["height"]
        left, top, w, h = CONFIG.region.to_pixels(self.screen_w, self.screen_h)
        self._bbox = {"left": left, "top": top, "width": w, "height": h}

    @property
    def bbox(self) -> dict[str, int]:
        return dict(self._bbox)

    def grab(self) -> np.ndarray:
        raw = np.asarray(self._sct.grab(self._bbox))
        return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)


class BarDetector:
    """Поиск циан-зоны (slider в терминологии игры) и жёлтого маркера.

    HSV-маски считаются с переиспользуемыми буферами через `dst=` параметр cv2,
    чтобы не аллоцировать ndarray каждый кадр.
    """

    def __init__(self) -> None:
        self._zone_lo = _hsv_bound(CONFIG.zone_hsv, lower=True)
        self._zone_hi = _hsv_bound(CONFIG.zone_hsv, lower=False)
        self._slider_lo = _hsv_bound(CONFIG.slider_hsv, lower=True)
        self._slider_hi = _hsv_bound(CONFIG.slider_hsv, lower=False)
        self._hsv: np.ndarray | None = None
        self._zone_mask: np.ndarray | None = None
        self._slider_mask: np.ndarray | None = None

    def detect(self, img_bgr: np.ndarray) -> Detection:
        self._hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV, dst=self._hsv)
        self._zone_mask = cv2.inRange(self._hsv, self._zone_lo, self._zone_hi, dst=self._zone_mask)
        self._slider_mask = cv2.inRange(self._hsv, self._slider_lo, self._slider_hi, dst=self._slider_mask)

        zone_run = _largest_run(self._zone_mask, CONFIG.min_zone_width_px)
        if zone_run is None:
            slider_x = _centroid_x(self._slider_mask, CONFIG.min_slider_area_px)
            return Detection(None, None, slider_x)

        slider_x = _centroid_x_in_window(
            self._slider_mask, zone_run, CONFIG.slider_search_margin_px,
            CONFIG.min_slider_area_px,
        )
        if slider_x is None:
            slider_x = _centroid_x(self._slider_mask, CONFIG.min_slider_area_px)
        return Detection(zone_run[0], zone_run[1], slider_x)


def _hsv_bound(rng: HSVRange, *, lower: bool) -> np.ndarray:
    triple = rng.lower() if lower else rng.upper()
    return np.array(triple, dtype=np.uint8)


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
