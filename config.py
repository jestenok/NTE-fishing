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
    use_rt_jitter: bool = False           # log-normal шум на reaction delay
    use_anticipation: bool = False        # предсказание по скорости ползунка
    use_prediction_noise: bool = False    # шум предсказания
    use_warmup: bool = False              # медленная реакция в начале сессии
    use_fatigue: bool = False             # RT растёт со временем
    use_reversal_penalty: bool = False    # +ms при смене направления
    use_rhythm_bonus: bool = False        # −ms при продолжении того же
    use_press_duration_scaling: bool = True   # ← ВКЛ: длительность нажатия ~ ошибке
    use_emergency_break: bool = True      # ← ВКЛ: сброс lock если маркер ушёл в обратную сторону
    use_miss: bool = False                # случайные промахи
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
    press_max_ms: float = 60.0

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

    pause_chance: float = 0.16            # ~раз в 12 решений
    pause_median_ms: float = 60.0         # короткая, чтобы маркер не успел улететь
    pause_only_within_err_px: int = 8     # пауза только если ползунок близко к центру

    rt_min_ms: float = 70.0
    rt_max_ms: float = 259.0


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

    deadband_px: int = 4
    fps: int = 60

    hotkey_toggle: str = "f8"
    hotkey_quit: str = "f9"

    min_zone_width_px: int = 8
    min_slider_area_px: int = 2

    humanizer: HumanizerConfig = field(default_factory=HumanizerConfig)


CONFIG = Config()
