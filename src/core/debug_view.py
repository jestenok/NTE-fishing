"""Окно отладки: весь экран с рамками отслеживаемых регионов.

Это ОТДЕЛЬНОЕ окно OpenCV, а НЕ оверлей поверх игры. Бот делает снимок
экрана и рисует рамки в СВОём окне; с процессом игры не взаимодействует и
ничего поверх неё не рисует — для системы это обычное окно приложения.

Включается флагом GameProfile.debug_view. По умолчанию выключено: при
debug_view=False объект DebugView вообще не создаётся, окна нет.
"""
import time

import cv2
import numpy as np

from core.capture import ScreenCapture
from core.geometry import Region

_OK_COLOR = (0, 220, 0)    # BGR, зелёный — объект задетектен
_MISS_COLOR = (0, 0, 220)  # BGR, красный — не задетектен
_MAX_W = 1280              # окно не шире этого — большой экран ужимаем
_FPS = 15                  # частота обновления окна (бот крутится быстрее)


class DebugView:
    """Одно OpenCV-окно: снимок всего экрана + рамки регионов модулей."""

    label = "отдельное окно OpenCV со снимком экрана (не оверлей)"

    def __init__(self, window_name: str = "vision-bot debug") -> None:
        self._win = window_name
        self._screen = ScreenCapture(Region(0.0, 0.0, 1.0, 1.0))
        self._interval = 1.0 / _FPS
        self._last = 0.0
        self._open = False

    def render(self, blocks: list[tuple[str, dict, bool]], running: bool) -> None:
        """blocks: список (имя модуля, bbox-словарь mss, флаг детекции)."""
        now = time.perf_counter()
        if now - self._last < self._interval:
            return
        self._last = now
        if self._open and not self._alive():
            self._open = False  # окно закрыли крестиком — пересоздать заново
        frame = self._screen.grab()
        self._draw_status(frame, running)
        for name, bbox, ok in blocks:
            self._draw_block(frame, name, bbox, ok)
        if not self._open:
            cv2.namedWindow(self._win, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(self._win, cv2.WND_PROP_TOPMOST, 1.0)
            cv2.resizeWindow(self._win, 960, 540)  # ← стартовый размер окна
        cv2.imshow(self._win, self._fit(frame))
        cv2.waitKey(1)
        self._open = True

    @staticmethod
    def _draw_status(frame: np.ndarray, running: bool) -> None:
        text = "BOT: ON" if running else "BOT: OFF"
        color = _OK_COLOR if running else _MISS_COLOR
        cv2.putText(frame, text, (12, 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    @staticmethod
    def _draw_block(frame: np.ndarray, name: str, bbox: dict, ok: bool) -> None:
        color = _OK_COLOR if ok else _MISS_COLOR
        x, y = bbox["left"], bbox["top"]
        w, h = bbox["width"], bbox["height"]
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        label = f"{name}: {'DETECTED' if ok else '---'}"
        cv2.putText(frame, label, (x + 4, max(y - 8, 16)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def _alive(self) -> bool:
        """Существует ли окно (False — пользователь закрыл его крестиком)."""
        try:
            return cv2.getWindowProperty(self._win, cv2.WND_PROP_VISIBLE) >= 1
        except cv2.error:
            return False

    @staticmethod
    def _fit(frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        if w <= _MAX_W:
            return frame
        return cv2.resize(frame, (_MAX_W, round(h * _MAX_W / w)))

    def close(self) -> None:
        if self._open:
            cv2.destroyWindow(self._win)
            cv2.waitKey(1)
            self._open = False
