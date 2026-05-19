from typing import Protocol, runtime_checkable


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
