"""
Точка входа. F8 — старт/пауза, F9 — выход.

Активный профиль задаётся первым аргументом CLI:
    python bot.py nte_fishing
Без аргумента — интерактивное меню со списком профилей.
"""
import argparse

from core.io_utils import ensure_utf8_stdout
from core.runner import GameBot
from profiles.base import discover_profiles, load_profile

QUICK_START_NTE_FISHING = True

ensure_utf8_stdout()


def pick_profile_interactively() -> str:
    names = discover_profiles()
    if not names:
        raise SystemExit("в src/profiles/ нет профилей")
    print("Доступные профили:")
    for i, n in enumerate(names, 1):
        print(f"  {i}. {n}")
    while True:
        raw = input(f"Выбери [1-{len(names)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(names):
            return names[int(raw) - 1]
        if raw in names:
            return raw
        print("не понял, попробуй ещё раз")


def main() -> None:
    parser = argparse.ArgumentParser(description="vision-bot")
    parser.add_argument(
        "profile",
        nargs="?",
        help="имя модуля в src/profiles/ без .py; если не задано — покажет меню",
    )
    args = parser.parse_args()
    if QUICK_START_NTE_FISHING:
        name = "nte_fishing"
    else:
        name = args.profile or pick_profile_interactively()
    GameBot(load_profile(name)).run()


if __name__ == "__main__":
    main()
