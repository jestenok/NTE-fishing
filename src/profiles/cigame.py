"""Профиль игры reaction-test — тест на реакцию.

Регион в случайный момент становится зелёным — бот сразу кликает мышью.
Запуск: python bot.py reaction-test

Реализован обычным сторожем (WatcherConfig) с действием-кликом: «регион
позеленел → клик» — это тот же автомат, что и у UI-сторожей рыбалки.

Зелёный HSV-диапазон, скорее всего, придётся подогнать под игру
(debug=True → смотри значение pixels= в консоли).
"""
from core.actions import MouseClick, KeyPress
from core.geometry import Region
from core.hsv import HSVRange
from core.watcher import WatcherConfig
from profiles.base import GameProfile

_reaction = WatcherConfig(
    name="reaction",
    region=Region(x1=0.145, y1=0.681, x2=0.805, y2=0.682),
    hsv=[HSVRange(0, 0, 200, 180, 40, 255)],  # белый: любой H, низкая S, высокая V
    action=KeyPress("space"),
    min_fill=0.5,             # ≥50% площади региона белое → срабатываем
    delay_s=(0.0, 0.0),     # задержка реакции; (0.0, 0.0) = кликать мгновенно
    cooldown_s=None,          # после клика ждём, пока белое не пропадёт
    debug=True,
)

PROFILE = GameProfile(
    name="cigame",
    fps=60,
    hotkey_toggle="f3",
    hotkey_quit="f4",
    modules=[_reaction],
    debug_view=True,
)
