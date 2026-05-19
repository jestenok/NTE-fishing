"""
Точка входа.

  python bot.py             — запустить активный профиль (settings.ACTIVE_PROFILE)
  python bot.py <профиль>   — запустить конкретный профиль из profiles/

F8 — старт/пауза, F9 — выход.
"""
import sys

from core.io_utils import ensure_utf8_stdout
from core.runner import GameBot
from profiles.base import load_profile
from settings import ACTIVE_PROFILE

ensure_utf8_stdout()


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else ACTIVE_PROFILE
    profile = load_profile(name)
    GameBot(profile).run()


if __name__ == "__main__":
    main()
