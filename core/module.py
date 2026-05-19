from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Module(Protocol):
    """Один независимый блок бота.

    Модуль сам захватывает свою область экрана, детектит и действует.
    GameBot просто прокручивает список модулей кадр за кадром.
    """

    name: str

    def tick(self, now: float) -> str | None:
        """Один кадр работы. Возвращает строку для лога, если что-то сделал."""
        ...

    def on_stop(self) -> None:
        """Сброс при паузе/выходе — отпустить клавиши, обнулить состояние."""
        ...

    def debug_panel(self) -> tuple[np.ndarray, bool] | None:
        """Кадр для окна отладки + флаг «объект задетектен».

        Возвращает (изображение BGR, detected) или None, если показывать
        пока нечего (модуль ещё не делал tick).
        """
        ...
