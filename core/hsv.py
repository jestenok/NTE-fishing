from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class HSVRange:
    """Диапазон цвета в пространстве HSV для cv2.inRange."""
    h_lo: int
    s_lo: int
    v_lo: int
    h_hi: int
    s_hi: int
    v_hi: int

    def lower(self) -> tuple[int, int, int]:
        return (self.h_lo, self.s_lo, self.v_lo)

    def upper(self) -> tuple[int, int, int]:
        return (self.h_hi, self.s_hi, self.v_hi)

    def lo_array(self) -> np.ndarray:
        return np.array(self.lower(), dtype=np.uint8)

    def hi_array(self) -> np.ndarray:
        return np.array(self.upper(), dtype=np.uint8)


def mask_one(img_bgr: np.ndarray, rng: HSVRange) -> np.ndarray:
    """Бинарная маска по одному HSV-диапазону."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, rng.lo_array(), rng.hi_array())


def mask_any(img_bgr: np.ndarray, ranges: list[HSVRange]) -> np.ndarray:
    """OR-маска по нескольким HSV-диапазонам (объединение цветов)."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    out: np.ndarray | None = None
    for rng in ranges:
        m = cv2.inRange(hsv, rng.lo_array(), rng.hi_array())
        out = m if out is None else cv2.bitwise_or(out, m)
    return out
