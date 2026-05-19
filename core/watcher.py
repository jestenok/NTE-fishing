import random
import time
from dataclasses import dataclass, field

import cv2
import pydirectinput

from core.capture import ScreenCapture
from core.geometry import Region
from core.hsv import HSVRange, mask_any

pydirectinput.PAUSE = 0
pydirectinput.FAILSAFE = False


@dataclass
class WatcherConfig:
    """Сторож: ждёт появления чего-то в области экрана и жмёт клавишу.

    Признак появления — суммарная площадь пикселей, попавших хотя бы в один
    из HSV-диапазонов `hsv`, достигает `min_pixels`.

    Поведение после нажатия задаётся `cooldown_s`:
      None     → ждём, пока картинка не пропадёт с экрана (как экран награды:
                 пока виден — повторно не жмём, пропал — снова готовы).
      (a, b)   → глухая пауза a..b секунд независимо от картинки
                 (как баннеры, чтобы не задолбить клавишу).
    """
    name: str
    region: Region
    hsv: list[HSVRange]
    min_pixels: int
    key: str
    delay_s: tuple[float, float] = (0.3, 1.5)
    cooldown_s: tuple[float, float] | None = None
    hold_ms: tuple[float, float] = (30.0, 90.0)
    debug: bool = False

    def build(self) -> "RegionWatcher":
        return RegionWatcher(self)


class RegionWatcher:
    """Конечный автомат: IDLE → SCHEDULED → COOLDOWN → IDLE.

      idle      — картинки нет, ждём появления
      scheduled — появилась, нажатие запланировано на act_at
      cooldown  — нажали, ждём (по таймеру или по пропаданию картинки)
    """

    IDLE = "idle"
    SCHEDULED = "scheduled"
    COOLDOWN = "cooldown"

    def __init__(self, cfg: WatcherConfig) -> None:
        self.cfg = cfg
        self.name = cfg.name
        self._cap = ScreenCapture(cfg.region)
        self.state = self.IDLE
        self._act_at = 0.0
        self._cooldown_until = 0.0
        self._last_debug = 0.0

    def _visible(self, now: float) -> bool:
        frame = self._cap.grab()
        mask = mask_any(frame, self.cfg.hsv)
        n = int(cv2.countNonZero(mask))
        if self.cfg.debug and now - self._last_debug >= 1.0:
            self._last_debug = now
            print(f"[{self.name}] pixels={n} thr={self.cfg.min_pixels} st={self.state}")
        return n >= self.cfg.min_pixels

    def _tap(self) -> None:
        pydirectinput.keyDown(self.cfg.key)
        time.sleep(random.uniform(*self.cfg.hold_ms) / 1000.0)
        pydirectinput.keyUp(self.cfg.key)

    def tick(self, now: float) -> str | None:
        visible = self._visible(now)

        if self.state == self.COOLDOWN:
            if self.cfg.cooldown_s is None:
                if not visible:
                    self.state = self.IDLE
            elif now >= self._cooldown_until:
                self.state = self.IDLE
            return None

        if self.state == self.IDLE:
            if visible:
                self._act_at = now + random.uniform(*self.cfg.delay_s)
                self.state = self.SCHEDULED
            return None

        # SCHEDULED
        if not visible:
            self.state = self.IDLE
            return None
        if now >= self._act_at:
            self._tap()
            if self.cfg.cooldown_s is not None:
                self._cooldown_until = now + random.uniform(*self.cfg.cooldown_s)
            self.state = self.COOLDOWN
            return f"{self.cfg.key.upper()} нажата"
        return None

    def on_stop(self) -> None:
        self.state = self.IDLE
