"""Профиль игры по умолчанию — рыбалка (исходная игра проекта).

Скопируй этот файл под другим именем, чтобы сделать профиль новой игры,
и подгони регионы/цвета/клавиши. Регионы, цвета и калибровку слайдера
удобно подбирать через `tools.py` (Pick color / Measure region / Calibrate slider).
"""
from core.geometry import Region
from core.humanizer import HumanizerConfig
from core.hsv import HSVRange
from core.actions import KeyPress
from core.watcher import WatcherConfig
from mechanics.slider import SliderConfig
from profiles.base import GameProfile, DebugView

# --- Основная мини-игра: полоса с циан-зоной и жёлтым ползунком --------------
_slider = SliderConfig(
    name="fishing",
    region=Region(x1=0.305, y1=0.060, x2=0.700, y2=0.080),
    zone_hsv=HSVRange(84, 200, 200, 113, 239, 229),    # циан-зона (цель)
    slider_hsv=HSVRange(20, 95, 240, 30, 115, 255),  # жёлтый ползунок
    key_left="a",
    key_right="d",
    invert_keys=False,        # переключить, если бот тянет в обратную сторону
    deadband_px=80,           # внутри ±5 px — клавиши отпущены, бот «стоит»
    engage_threshold_px=100,   # снова жмём только если ушло за ±5 px (широкий гистерезис)
    slider_search_margin_px=200,
    min_zone_width_px=8,
    min_slider_area_px=2,
    humanizer=HumanizerConfig(),
    debug=False,
)

# --- Экран награды после поимки рыбы → ESC -----------------------------------
# Тёмная плашка-капсула «Уровень рыбалки X · NNN/MMMM · +K» вверху по центру.
# Появляется всегда. Признак — большая зона очень тёмных пикселей (V<70).
# cooldown_s=None: пока плашка видна — повторно не жмём.
_reward = WatcherConfig(
    name="reward",
    region=Region(x1=0.42, y1=0.1, x2=0.443, y2=0.126),
    hsv=[HSVRange(0, 0, 180, 179, 30, 230)],
    min_fill=0.50,
    action=KeyPress("esc"),
    delay_s=(0.3, 1.5),
    cooldown_s=None,
)

# --- Баннер «Рыба на крючке!» вверху по центру → F ---------------------------
# Тёмная горизонтальная плашка с белым текстом в узкой Y-полосе сверху.
_banner = WatcherConfig(
    name="banner",
    region=Region(x1=0.44, y1=0.24, x2=0.502, y2=0.255),
    hsv=[HSVRange(0, 0, 180, 179, 30, 230)],
    min_fill=0.2,
    action=KeyPress("f"),
    delay_s=(0.3, 1.5),
    cooldown_s=(7, 9),
    debug=True,
)

# --- Иконка-промпт «нажми F» в правом нижнем углу → F ------------------------
# OR двух масок: яркий cyan кант активной рыбалки + светлый белый крючок idle.
_interact = WatcherConfig(
    name="interact",
    region=Region(x1=0.90, y1=0.85, x2=0.95, y2=0.97),
    hsv=[
        HSVRange(85, 80, 100, 130, 255, 255),  # cyan кант
        HSVRange(0, 0, 140, 180, 80, 255),     # белый крючок
    ],
    min_pixels=25,
    action=KeyPress("f"),
    delay_s=(0.2, 1.5),
    cooldown_s=(10, 12),
    debug=True,
)

PROFILE = GameProfile(
    name="nte_fishing",
    fps=6,
    hotkey_toggle="f3",
    hotkey_quit="f4",
    debug_view=DebugView.OVERLAY,
    modules=[_slider, _reward, _banner, _interact],
)
