import cv2
import mss
import numpy as np

from core.geometry import Region


class ScreenCapture:
    """Захват прямоугольной области экрана через mss."""

    def __init__(self, region: Region) -> None:
        self._sct = mss.MSS()
        monitor = self._sct.monitors[1]
        self.screen_w: int = monitor["width"]
        self.screen_h: int = monitor["height"]
        left, top, w, h = region.to_pixels(self.screen_w, self.screen_h)
        self._bbox = {"left": left, "top": top, "width": w, "height": h}

    @property
    def bbox(self) -> dict[str, int]:
        return dict(self._bbox)

    def grab(self) -> np.ndarray:
        raw = np.asarray(self._sct.grab(self._bbox))
        return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
