import importlib
from dataclasses import dataclass
from typing import Protocol

from core.module import Module


class ModuleConfig(Protocol):
    """Конфиг модуля умеет построить рантайм-модуль (SliderConfig, WatcherConfig …)."""

    def build(self) -> Module: ...


@dataclass
class GameProfile:
    """Профиль одной игры: список модулей + параметры цикла.

    `modules` — это конфиги (SliderConfig, WatcherConfig, …), у каждого свой
    метод `.build()`. Чтобы добавить игру — создай profiles/<имя>.py с
    переменной модульного уровня `PROFILE = GameProfile(...)`.
    """
    name: str
    modules: list[ModuleConfig]
    fps: int = 60
    hotkey_toggle: str = "f8"
    hotkey_quit: str = "f9"

    def build_modules(self) -> list[Module]:
        return [m.build() for m in self.modules]


def load_profile(name: str) -> GameProfile:
    """Грузит profiles/<name>.py и возвращает определённый там PROFILE."""
    try:
        mod = importlib.import_module(f"profiles.{name}")
    except ModuleNotFoundError as exc:
        raise SystemExit(f"профиль не найден: profiles/{name}.py") from exc
    profile = getattr(mod, "PROFILE", None)
    if not isinstance(profile, GameProfile):
        raise SystemExit(
            f"profiles/{name}.py должен определять PROFILE = GameProfile(...)"
        )
    return profile
