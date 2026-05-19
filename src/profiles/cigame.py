"""Профиль игры cigame.

Реализован обычным сторожем (WatcherConfig) с действием-кликом: «регион
позеленел → клик» — это тот же автомат, что и у UI-сторожей рыбалки.

Зелёный HSV-диапазон, скорее всего, придётся подогнать под игру
(debug=True → смотри значение pixels= в консоли).
"""
from core.actions import MouseClick, KeyPress
from core.geometry import Region
from core.hsv import HSVRange
from core.watcher import WatcherConfig
from profiles.base import DebugView, GameProfile

_reaction = WatcherConfig(
    name="reaction",
    region=Region(x1=0.450, y1=0.675, x2=0.500, y2=0.685),
    hsv=[HSVRange(0, 0, 60, 90, 255, 255)],  # белый: любой H, низкая S, высокая V
    action=KeyPress("space", (0.05, 0.1)),  # клик по центру региона
    min_fill=0.5,             # ≥50% площади региона белое → срабатываем
    delay_s=(0.0, 0.0),     # задержка реакции; (0.0, 0.0) = кликать мгновенно
    cooldown_s=None,          # после клика ждём, пока белое не пропадёт
    debug=True,
)

PROFILE = GameProfile(
    name="cigame",
    fps=180,
    hotkey_toggle="f3",
    hotkey_quit="f4",
    modules=[_reaction],
    debug_view=DebugView.OFF,
)
