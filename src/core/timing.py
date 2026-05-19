"""Стратегии задержек: пауза перед действием (Delay) и после него (Cooldown).

Конкретная стратегия выбирается один раз — на этапе билда модуля (make_*),
поэтому в горячем цикле нет ветвлений, только полиморфный вызов.
"""
import random
from typing import Protocol


# --- Задержка перед срабатыванием -------------------------------------------

class Delay(Protocol):
    """Стратегия паузы перед срабатыванием."""

    def next(self) -> float: ...


class NoDelay:
    """Нулевая задержка — срабатывать сразу, без расчётов."""

    def next(self) -> float:
        return 0.0


class RandomDelay:
    """Случайная задержка в диапазоне [lo, hi] секунд."""

    def __init__(self, lo: float, hi: float) -> None:
        self._lo = lo
        self._hi = hi

    def next(self) -> float:
        return random.uniform(self._lo, self._hi)


def make_delay(delay_s: tuple[float, float]) -> Delay:
    """Выбирает стратегию задержки по диапазону (lo, hi)."""
    if delay_s[0] <= 0.0 and delay_s[1] <= 0.0:
        return NoDelay()
    return RandomDelay(*delay_s)


# --- Кулдаун после срабатывания ---------------------------------------------

class Cooldown(Protocol):
    """Стратегия паузы после срабатывания.

    `present` — внешний признак того, что триггер всё ещё активен
    (для сторожа это «картинка ещё видна на экране»).
    """

    def start(self, now: float) -> None: ...

    def expired(self, now: float, present: bool) -> bool: ...


class UntilGone:
    """Кулдаун держится, пока триггер присутствует; снят, когда исчез."""

    def start(self, now: float) -> None:
        pass

    def expired(self, now: float, present: bool) -> bool:
        return not present


class TimerCooldown:
    """Кулдаун — фиксированная случайная пауза [lo, hi] секунд."""

    def __init__(self, lo: float, hi: float) -> None:
        self._lo = lo
        self._hi = hi
        self._until = 0.0

    def start(self, now: float) -> None:
        self._until = now + random.uniform(self._lo, self._hi)

    def expired(self, now: float, present: bool) -> bool:
        return now >= self._until


def make_cooldown(cooldown_s: tuple[float, float] | None) -> Cooldown:
    """Выбирает стратегию кулдауна: None → ждать пропадания, (lo, hi) → таймер."""
    if cooldown_s is None:
        return UntilGone()
    return TimerCooldown(*cooldown_s)
