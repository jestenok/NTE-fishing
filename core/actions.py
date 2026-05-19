"""Действия сторожа при срабатывании: нажать клавишу или кликнуть мышью."""
import random
import time
from dataclasses import dataclass
from typing import Protocol

import pydirectinput

pydirectinput.PAUSE = 0
pydirectinput.FAILSAFE = False


class Action(Protocol):
    """Что сделать, когда сторож засёк появление картинки."""

    def perform(self) -> None: ...

    def label(self) -> str:
        """Короткое описание для лога."""
        ...


@dataclass
class KeyPress:
    """Нажатие клавиши клавиатуры с человекоподобным удержанием."""
    key: str
    hold_ms: tuple[float, float] = (30.0, 90.0)

    def perform(self) -> None:
        pydirectinput.keyDown(self.key)
        time.sleep(random.uniform(*self.hold_ms) / 1000.0)
        pydirectinput.keyUp(self.key)

    def label(self) -> str:
        return f"{self.key.upper()} нажата"


@dataclass
class MouseClick:
    """Клик мышью в текущей позиции курсора."""
    button: str = "left"  # left / right / middle

    def perform(self) -> None:
        pydirectinput.click(button=self.button)

    def label(self) -> str:
        return f"клик ({self.button})"
