"""Профиль игры reaction-test — тест на реакцию.

Регион в случайный момент становится зелёным — бот сразу кликает мышью.

Реализован обычным сторожем (WatcherConfig) с действием-кликом: «регион
позеленел → клик» — это тот же автомат, что и у UI-сторожей рыбалки.

Зелёный HSV-диапазон, скорее всего, придётся подогнать под игру
(debug=True → смотри значение pixels= в консоли).
"""
from core.actions import MouseClick
from core.geometry import Region
from core.hsv import HSVRange
from core.watcher import WatcherConfig
from profiles.base import DebugView, GameProfile

_reaction = WatcherConfig(
    name="reaction",
    region=Region(x1=0.283, y1=0.348, x2=0.290, y2=0.370),
    hsv=[HSVRange(35, 60, 60, 90, 255, 255)],  # ярко-зелёный; подгони при необходимости
    action=MouseClick("left"),  # клик по центру региона
    min_fill=0.5,             # ≥50% площади региона зелёное → "позеленел"
    delay_s=(0.0, 0.0),     # задержка реакции; (0.0, 0.0) = кликать мгновенно
    cooldown_s=None,          # после клика ждём, пока зелёный не пропадёт
    debug=True,
)

PROFILE = GameProfile(
    name="reaction-test",
    fps=160,
    hotkey_toggle="f3",
    hotkey_quit="f4",
    modules=[_reaction],
    debug_view=DebugView.OVERLAY,
)
