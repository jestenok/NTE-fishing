"""Окно отладки: показывает, что бот вырезает с экрана и что детектит.

Это ОТДЕЛЬНОЕ окно OpenCV, а НЕ оверлей поверх игры. С процессом игры
никак не взаимодействует и ничего поверх неё не рисует — для системы это
обычное окно приложения.

Включается флагом GameProfile.debug_view. По умолчанию выключено: при
debug_view=False объект DebugView вообще не создаётся, окна нет.
"""
import cv2
import numpy as np

_PANEL_WIDTH = 480
_LABEL_H = 24
_BORDER = 3
_OK_COLOR = (0, 220, 0)    # BGR, зелёный — объект задетектен
_MISS_COLOR = (0, 0, 220)  # BGR, красный — не задетектен


class DebugView:
    """Одно OpenCV-окно с панелями — по панели на модуль бота."""

    def __init__(self, window_name: str = "vision-bot debug") -> None:
        self._win = window_name
        self._open = False

    def render(self, panels: list[tuple[str, np.ndarray, bool]]) -> None:
        """panels: список (имя модуля, кадр BGR, флаг детекции)."""
        rows = [
            self._panel(name, img, ok)
            for name, img, ok in panels
            if img is not None
        ]
        if not rows:
            return
        cv2.imshow(self._win, np.vstack(rows))
        cv2.waitKey(1)
        self._open = True

    @staticmethod
    def _panel(name: str, img: np.ndarray, ok: bool) -> np.ndarray:
        h = max(1, round(img.shape[0] * _PANEL_WIDTH / img.shape[1]))
        view = cv2.resize(img, (_PANEL_WIDTH, h))
        color = _OK_COLOR if ok else _MISS_COLOR
        cv2.rectangle(view, (0, 0), (_PANEL_WIDTH - 1, h - 1), color, _BORDER)
        bar = np.zeros((_LABEL_H, _PANEL_WIDTH, 3), dtype=np.uint8)
        text = f"{name}: {'DETECTED' if ok else '---'}"
        cv2.putText(bar, text, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return np.vstack([bar, view])

    def close(self) -> None:
        if self._open:
            cv2.destroyWindow(self._win)
            cv2.waitKey(1)
            self._open = False
