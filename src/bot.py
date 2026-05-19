"""
Точка входа. F8 — старт/пауза, F9 — выход.

Активный профиль выбирается импортом ниже — IDE подскажет имена модулей.
"""
from core.io_utils import ensure_utf8_stdout
from core.runner import GameBot
from profiles.cigame import PROFILE

ensure_utf8_stdout()


def main() -> None:
    GameBot(PROFILE).run()


if __name__ == "__main__":
    main()
