from dataclasses import dataclass

import cv2

from core.actions import Action
from core.capture import ScreenCapture
from core.geometry import Region
from core.hsv import HSVRange, mask_any
from core.timing import make_cooldown, make_delay


@dataclass
class WatcherConfig:
    """Сторож: ждёт появления чего-то в области экрана и выполняет действие.

    Признак появления — суммарная площадь пикселей, попавших хотя бы в один
    из HSV-диапазонов `hsv`. Порог задаётся ровно одним из двух способов:
      min_pixels — абсолютное число пикселей;
      min_fill   — доля площади региона (0..1), не зависит от разрешения.

    `action` — что сделать при срабатывании (KeyPress / MouseClick из core.actions).

    Поведение после срабатывания задаётся `cooldown_s`:
      None     → ждём, пока картинка не пропадёт с экрана (пока видна —
                 повторно не срабатываем, пропала — снова готовы).
      (a, b)   → глухая пауза a..b секунд независимо от картинки.
    """
    name: str
    region: Region
    hsv: list[HSVRange]
    action: Action
    min_pixels: int | None = None
    min_fill: float | None = None
    delay_s: tuple[float, float] = (0.3, 1.5)
    cooldown_s: tuple[float, float] | None = None
    debug: bool = False

    def __post_init__(self) -> None:
        if (self.min_pixels is None) == (self.min_fill is None):
            raise ValueError(
                f"watcher '{self.name}': задай ровно одно из min_pixels / min_fill"
            )

    def build(self) -> "RegionWatcher":
        return RegionWatcher(self)


class RegionWatcher:
    """Конечный автомат: IDLE → SCHEDULED → COOLDOWN → IDLE.

      idle      — картинки нет, ждём появления
      scheduled — появилась, действие запланировано на act_at
      cooldown  — действие выполнено, ждём (по таймеру или по пропаданию картинки)
    """

    IDLE = "idle"
    SCHEDULED = "scheduled"
    COOLDOWN = "cooldown"

    def __init__(self, cfg: WatcherConfig) -> None:
        self.cfg = cfg
        self.name = cfg.name
        self._cap = ScreenCapture(cfg.region)
        self._threshold = self._resolve_threshold(cfg)
        self._delay = make_delay(cfg.delay_s)
        self._cooldown = make_cooldown(cfg.cooldown_s)
        self.state = self.IDLE
        self._act_at = 0.0
        self._last_debug = 0.0

    def _resolve_threshold(self, cfg: WatcherConfig) -> int:
        if cfg.min_fill is not None:
            bbox = self._cap.bbox
            return max(1, int(cfg.min_fill * bbox["width"] * bbox["height"]))
        return cfg.min_pixels

    def _visible(self, now: float) -> bool:
        frame = self._cap.grab()
        mask = mask_any(frame, self.cfg.hsv)
        n = int(cv2.countNonZero(mask))
        if self.cfg.debug and now - self._last_debug >= 1.0:
            self._last_debug = now
            print(f"[{self.name}] pixels={n} thr={self._threshold} st={self.state}")
        return n >= self._threshold

    def tick(self, now: float) -> str | None:
        visible = self._visible(now)

        if self.state == self.COOLDOWN:
            if self._cooldown.expired(now, visible):
                self.state = self.IDLE
            return None

        if self.state == self.IDLE:
            if visible:
                self._act_at = now + self._delay.next()
                self.state = self.SCHEDULED
            return None

        # SCHEDULED
        if not visible:
            self.state = self.IDLE
            return None
        if now >= self._act_at:
            self.cfg.action.perform()
            self._cooldown.start(now)
            self.state = self.COOLDOWN
            return self.cfg.action.label()
        return None

    def on_stop(self) -> None:
        self.state = self.IDLE
