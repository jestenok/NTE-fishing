"""Профиль игры по умолчанию — рыбалка (исходная игра проекта).

Скопируй этот файл под другим именем, чтобы сделать профиль новой игры,
и подгони регионы/цвета/клавиши. Регионы удобно мерить через `measure.py`,
цвета — проверять через `calibrate.py`.
"""
from core.geometry import Region
from core.humanizer import HumanizerConfig
from core.hsv import HSVRange
from core.watcher import WatcherConfig
from mechanics.slider import SliderConfig
from profiles.base import GameProfile

# --- Основная мини-игра: полоса с циан-зоной и жёлтым ползунком --------------
_slider = SliderConfig(
    name="fishing",
    region=Region(x1=0.305, y1=0.030, x2=0.700, y2=0.080),
    zone_hsv=HSVRange(60, 80, 140, 100, 255, 255),    # циан-зона (цель)
    slider_hsv=HSVRange(18, 120, 180, 38, 255, 255),  # жёлтый ползунок
    key_left="a",
    key_right="d",
    invert_keys=False,        # переключить, если бот тянет в обратную сторону
    deadband_px=4,
    engage_threshold_px=9,
    slider_search_margin_px=8,
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
    region=Region(x1=0.40, y1=0.10, x2=0.66, y2=0.16),
    hsv=[HSVRange(0, 0, 0, 180, 100, 70)],
    min_pixels=2000,
    key="esc",
    delay_s=(0.3, 1.5),
    cooldown_s=None,
)

# --- Баннер «Рыба на крючке!» вверху по центру → F ---------------------------
# Тёмная горизонтальная плашка с белым текстом в узкой Y-полосе сверху.
_banner = WatcherConfig(
    name="banner",
    region=Region(x1=0.28, y1=0.21, x2=0.72, y2=0.30),
    hsv=[HSVRange(0, 0, 0, 180, 80, 70)],
    min_pixels=2000,
    key="f",
    delay_s=(0.3, 1.5),
    cooldown_s=(3.0, 6.0),
    debug=True,
)

# --- Иконка-промпт «нажми F» в правом нижнем углу → F ------------------------
# OR двух масок: яркий cyan кант активной рыбалки + светлый белый крючок idle.
_interact = WatcherConfig(
    name="interact",
    region=Region(x1=0.90, y1=0.83, x2=1.00, y2=0.99),
    hsv=[
        HSVRange(85, 80, 100, 130, 255, 255),  # cyan кант
        HSVRange(0, 0, 140, 180, 80, 255),     # белый крючок
    ],
    min_pixels=25,
    key="f",
    delay_s=(0.3, 1.5),
    cooldown_s=(1.5, 3.0),
    debug=True,
)

PROFILE = GameProfile(
    name="default",
    fps=60,
    hotkey_toggle="f8",
    hotkey_quit="f9",
    modules=[_slider, _reward, _banner, _interact],
)
