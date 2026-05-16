from dataclasses import dataclass, field


@dataclass
class Region:
    x1: float = 0.305
    y1: float = 0.030
    x2: float = 0.700
    y2: float = 0.080

    def to_pixels(self, screen_w: int, screen_h: int) -> tuple[int, int, int, int]:
        left = int(self.x1 * screen_w)
        top = int(self.y1 * screen_h)
        right = int(self.x2 * screen_w)
        bottom = int(self.y2 * screen_h)
        return left, top, right - left, bottom - top


@dataclass
class HSVRange:
    h_lo: int
    s_lo: int
    v_lo: int
    h_hi: int
    s_hi: int
    v_hi: int

    def lower(self):
        return (self.h_lo, self.s_lo, self.v_lo)

    def upper(self):
        return (self.h_hi, self.s_hi, self.v_hi)


@dataclass
class HumanizerConfig:
    enabled: bool = True

    # === ФИЧЕФЛАГИ — включай по одному ===
    use_rt_jitter: bool = True            # log-normal шум на reaction delay
    use_anticipation: bool = True         # предсказание по скорости ползунка
    use_prediction_noise: bool = True     # шум предсказания
    use_warmup: bool = True               # медленная реакция в начале сессии
    use_fatigue: bool = True              # RT растёт со временем
    use_reversal_penalty: bool = True     # +ms при смене направления
    use_rhythm_bonus: bool = True         # −ms при продолжении того же
    use_press_duration_scaling: bool = True   # ← ВКЛ: длительность нажатия ~ ошибке
    use_emergency_break: bool = True      # ← ВКЛ: сброс lock если маркер ушёл в обратную сторону
    use_miss: bool = True                 # случайные промахи
    use_pause: bool = True                # ← ВКЛ: иногда "стоит на месте" вместо нажатия

    # === значения параметров (используются только если соответствующий флаг True) ===
    reaction_median_ms: float = 16.0      # базовая задержка минимальна — игра слишком быстрая
    reaction_sigma: float = 0.28
    reversal_penalty_ms: float = 45.0
    rhythm_bonus_ms: float = 25.0
    warmup_extra_ms: float = 80.0
    warmup_seconds: float = 2.0
    fatigue_ms_per_min: float = 1.2
    fatigue_cap_ms: float = 60.0

    anticipation_ms: float = 40.0
    prediction_noise_px: float = 2.0
    velocity_window_s: float = 0.10

    press_base_ms: float = 10.0
    press_per_px_ms: float = 1.1
    press_sigma: float = 0.22
    press_min_ms: float = 30.0
    press_max_ms: float = 110.0

    release_hold_median_ms: float = 70.0

    emergency_break_px: int = 6

    miss_chance: float = 0.018
    miss_recovery_ms: float = 150.0
    miss_median_ms: float = 25.0
    miss_min_ms: float = 12.0
    miss_max_ms: float = 50.0
    miss_only_within_err_px: int = 5
    miss_correction_min_ms: float = 40.0
    miss_correction_max_ms: float = 100.0

    pause_chance: float = 0.64            # ~раз в 12 решений
    pause_median_ms: float = 60.0         # короткая, чтобы маркер не успел улететь
    pause_only_within_err_px: int = 8     # пауза только если ползунок близко к центру

    rt_min_ms: float = 70.0
    rt_max_ms: float = 259.0


@dataclass
class RewardScreenConfig:
    """Экран награды после поимки рыбы. Триггер — тёмная плашка-капсула
    «Уровень рыбалки X · NNN/MMMM · +K» вверху по центру. Она появляется
    всегда, даже когда розовый XP-бар внутри пустой (только что апнулся
    уровень). Признак — большая зона очень тёмных пикселей (V<70).
    """
    enabled: bool = True
    region: Region = field(default_factory=lambda: Region(x1=0.40, y1=0.10, x2=0.66, y2=0.16))
    panel_hsv: HSVRange = field(default_factory=lambda: HSVRange(0, 0, 0, 180, 100, 70))
    min_pixels: int = 2000
    esc_min_s: float = 0.3
    esc_max_s: float = 1.5
    esc_key: str = "esc"


@dataclass
class InteractPromptConfig:
    """Иконка-промпт «нажми F» в правом нижнем углу. Появляется → жмём F.

    Два кейса:
      a) Большой синий круг с белым крючком + cyan кольцо прогресс-бара
         (активная рыбалка). Признак — яркий cyan кант.
      b) Ряд иконок R/Q/E/F (idle, можно начать). Признак — светлый
         белый крючок в правой из четырёх иконок.
    Детектор берёт OR двух HSV-масок и сравнивает с `min_pixels`.
    """
    enabled: bool = True
    region: Region = field(default_factory=lambda: Region(x1=0.90, y1=0.83, x2=1.00, y2=0.99))
    cyan_hsv: HSVRange = field(default_factory=lambda: HSVRange(85, 80, 100, 130, 255, 255))
    white_hsv: HSVRange = field(default_factory=lambda: HSVRange(0, 0, 140, 180, 80, 255))
    min_pixels: int = 25
    delay_min_s: float = 0.3
    delay_max_s: float = 1.5
    cooldown_min_s: float = 1.5
    cooldown_max_s: float = 3.0
    key: str = "f"
    hold_min_ms: float = 30.0
    hold_max_ms: float = 90.0
    debug: bool = True


@dataclass
class FishCaughtBannerConfig:
    """Баннер «Рыба на крючке! Нажмите кнопку, чтобы вытащить!» вверху по центру.
    Тёмная горизонтальная плашка с белым текстом. Признак — большая зона
    низкой яркости (V<70, S<80) в узкой Y-полосе сверху.
    """
    enabled: bool = True
    region: Region = field(default_factory=lambda: Region(x1=0.28, y1=0.21, x2=0.72, y2=0.30))
    dark_hsv: HSVRange = field(default_factory=lambda: HSVRange(0, 0, 0, 180, 80, 70))
    min_pixels: int = 2000
    delay_min_s: float = 0.3
    delay_max_s: float = 1.5
    cooldown_min_s: float = 3.0
    cooldown_max_s: float = 6.0
    key: str = "f"
    hold_min_ms: float = 30.0
    hold_max_ms: float = 90.0
    debug: bool = True


@dataclass
class Config:
    region: Region = field(default_factory=Region)

    zone_hsv: HSVRange = field(default_factory=lambda: HSVRange(60, 80, 140, 100, 255, 255))
    slider_hsv: HSVRange = field(default_factory=lambda: HSVRange(18, 120, 180, 38, 255, 255))
    slider_search_margin_px: int = 8

    key_left: str = "a"
    key_right: str = "d"
    invert_keys: bool = False  # переключить если бот тянет в обратную сторону

    debug: bool = False  # подробный лог каждого кадра в консоль

    deadband_px: int = 4              # внутри ±этого — отпустить клавиши
    engage_threshold_px: int = 9      # снова нажимать только если ушло за ±этого (гистерезис)
    fps: int = 60

    hotkey_toggle: str = "f8"
    hotkey_quit: str = "f9"


    min_zone_width_px: int = 8
    min_slider_area_px: int = 2

    humanizer: HumanizerConfig = field(default_factory=HumanizerConfig)
    reward_screen: RewardScreenConfig = field(default_factory=RewardScreenConfig)
    interact_prompt: InteractPromptConfig = field(default_factory=InteractPromptConfig)
    fish_caught_banner: FishCaughtBannerConfig = field(default_factory=FishCaughtBannerConfig)


CONFIG = Config()
