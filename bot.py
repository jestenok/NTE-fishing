import random
import time
from dataclasses import dataclass

import cv2
import keyboard
import mss
import numpy as np
import pydirectinput

from config import (
    CONFIG,
    FishCaughtBannerConfig,
    InteractPromptConfig,
    RewardScreenConfig,
)
from controller import KeyHolder
from humanizer import LEFT, RELEASE, RIGHT, Humanizer
from io_utils import ensure_utf8_stdout
from vision import BarDetector, Detection, ScreenCapture

ensure_utf8_stdout()


@dataclass(slots=True)
class FrameStats:
    det: Detection
    action: str
    phys_key: str


class DebugLogger:
    """Печатает строку статуса не чаще, чем раз в `interval_s`."""

    def __init__(self, interval_s: float) -> None:
        self.interval_s = interval_s
        self._last = 0.0

    def maybe_log(self, now: float, stats: FrameStats, key_state: str) -> None:
        if now - self._last < self.interval_s:
            return
        self._last = now
        det = stats.det
        zc = det.zone_center if det.has_zone else None
        sx = det.slider_x if det.has_slider else None
        err = (sx - zc) if (sx is not None and zc is not None) else None
        sx_s = f"{sx:>4}" if sx is not None else "  — "
        zc_s = f"{zc:>4}" if zc is not None else "  — "
        err_s = f"{err:+4d}" if err is not None else "  — "
        print(
            f"[{key_state}] slider={sx_s} zone_c={zc_s} err={err_s}  "
            f"action={stats.action:<7} press={stats.phys_key}"
        )


class RewardScreenWatcher:
    """Ловит экран награды (розовый XP-бар вверху по центру) и жмёт ESC.

    Состояния:
      idle      — бара нет, готовы поймать появление
      scheduled — бар появился, ESC запланирован на esc_at
      cooldown  — ESC нажат, ждём пока бар пропадёт (анти-спам)
    """

    IDLE = "idle"
    SCHEDULED = "scheduled"
    COOLDOWN = "cooldown"

    def __init__(self, cfg: RewardScreenConfig) -> None:
        self.cfg = cfg
        self._sct = mss.MSS()
        mon = self._sct.monitors[1]
        left, top, w, h = cfg.region.to_pixels(mon["width"], mon["height"])
        self._bbox = {"left": left, "top": top, "width": w, "height": h}
        self._lo = np.array(cfg.panel_hsv.lower(), dtype=np.uint8)
        self._hi = np.array(cfg.panel_hsv.upper(), dtype=np.uint8)
        self.state = self.IDLE
        self.esc_at: float = 0.0

    def _bar_visible(self) -> bool:
        raw = np.asarray(self._sct.grab(self._bbox))
        bgr = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self._lo, self._hi)
        return int(cv2.countNonZero(mask)) >= self.cfg.min_pixels

    def tick(self, now: float) -> bool:
        visible = self._bar_visible()

        if self.state == self.IDLE:
            if visible:
                self.esc_at = now + random.uniform(self.cfg.esc_min_s, self.cfg.esc_max_s)
                self.state = self.SCHEDULED
            return False

        if self.state == self.SCHEDULED:
            if not visible:
                self.state = self.IDLE
                return False
            if now >= self.esc_at:
                pydirectinput.press(self.cfg.esc_key)
                self.state = self.COOLDOWN
                return True
            return False

        if not visible:
            self.state = self.IDLE
        return False


class FishCaughtBannerWatcher:
    """Ловит баннер «Рыба на крючке!» вверху по центру и жмёт F.

    State machine — как у InteractPromptWatcher: IDLE → SCHEDULED → COOLDOWN
    (по таймеру, не по visible).
    """

    IDLE = "idle"
    SCHEDULED = "scheduled"
    COOLDOWN = "cooldown"

    def __init__(self, cfg: FishCaughtBannerConfig) -> None:
        self.cfg = cfg
        self._sct = mss.MSS()
        mon = self._sct.monitors[1]
        left, top, w, h = cfg.region.to_pixels(mon["width"], mon["height"])
        self._bbox = {"left": left, "top": top, "width": w, "height": h}
        self._lo = np.array(cfg.dark_hsv.lower(), dtype=np.uint8)
        self._hi = np.array(cfg.dark_hsv.upper(), dtype=np.uint8)
        self.state = self.IDLE
        self.key_at: float = 0.0
        self.cooldown_until: float = 0.0
        self._last_debug: float = 0.0

    def _banner_visible(self, now: float) -> bool:
        raw = np.asarray(self._sct.grab(self._bbox))
        bgr = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self._lo, self._hi)
        n = int(cv2.countNonZero(mask))
        if self.cfg.debug and now - self._last_debug >= 1.0:
            self._last_debug = now
            print(f"[banner] dark={n} thr={self.cfg.min_pixels} st={self.state}")
        return n >= self.cfg.min_pixels

    def _tap_key(self) -> None:
        pydirectinput.keyDown(self.cfg.key)
        time.sleep(random.uniform(self.cfg.hold_min_ms, self.cfg.hold_max_ms) / 1000.0)
        pydirectinput.keyUp(self.cfg.key)

    def tick(self, now: float) -> bool:
        visible = self._banner_visible(now)

        if self.state == self.COOLDOWN:
            if now >= self.cooldown_until:
                self.state = self.IDLE
            return False

        if self.state == self.IDLE:
            if visible:
                self.key_at = now + random.uniform(self.cfg.delay_min_s, self.cfg.delay_max_s)
                self.state = self.SCHEDULED
            return False

        if not visible:
            self.state = self.IDLE
            return False
        if now >= self.key_at:
            self._tap_key()
            self.cooldown_until = now + random.uniform(
                self.cfg.cooldown_min_s, self.cfg.cooldown_max_s,
            )
            self.state = self.COOLDOWN
            return True
        return False


class InteractPromptWatcher:
    """Ловит иконку «нажми F» в правом нижнем углу и жмёт F.

    Состояния:
      idle      — иконки нет
      scheduled — иконка появилась, F запланирована на key_at
      cooldown  — F нажата, ждём пока иконка пропадёт
    """

    IDLE = "idle"
    SCHEDULED = "scheduled"
    COOLDOWN = "cooldown"

    def __init__(self, cfg: InteractPromptConfig) -> None:
        self.cfg = cfg
        self._sct = mss.MSS()
        mon = self._sct.monitors[1]
        left, top, w, h = cfg.region.to_pixels(mon["width"], mon["height"])
        self._bbox = {"left": left, "top": top, "width": w, "height": h}
        self._cyan_lo = np.array(cfg.cyan_hsv.lower(), dtype=np.uint8)
        self._cyan_hi = np.array(cfg.cyan_hsv.upper(), dtype=np.uint8)
        self._white_lo = np.array(cfg.white_hsv.lower(), dtype=np.uint8)
        self._white_hi = np.array(cfg.white_hsv.upper(), dtype=np.uint8)
        self.state = self.IDLE
        self.key_at: float = 0.0
        self.cooldown_until: float = 0.0
        self._last_debug: float = 0.0

    def _icon_visible(self, now: float) -> bool:
        raw = np.asarray(self._sct.grab(self._bbox))
        bgr = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        cyan = cv2.inRange(hsv, self._cyan_lo, self._cyan_hi)
        white = cv2.inRange(hsv, self._white_lo, self._white_hi)
        c, w = int(cv2.countNonZero(cyan)), int(cv2.countNonZero(white))
        total = int(cv2.countNonZero(cv2.bitwise_or(cyan, white)))
        if self.cfg.debug and now - self._last_debug >= 1.0:
            self._last_debug = now
            print(f"[prompt] cyan={c} white={w} or={total} thr={self.cfg.min_pixels} st={self.state}")
        return total >= self.cfg.min_pixels

    def _tap_key(self) -> None:
        pydirectinput.keyDown(self.cfg.key)
        time.sleep(random.uniform(self.cfg.hold_min_ms, self.cfg.hold_max_ms) / 1000.0)
        pydirectinput.keyUp(self.cfg.key)

    def tick(self, now: float) -> bool:
        visible = self._icon_visible(now)

        if self.state == self.COOLDOWN:
            if now >= self.cooldown_until:
                self.state = self.IDLE
            return False

        if self.state == self.IDLE:
            if visible:
                self.key_at = now + random.uniform(self.cfg.delay_min_s, self.cfg.delay_max_s)
                self.state = self.SCHEDULED
            return False

        if not visible:
            self.state = self.IDLE
            return False
        if now >= self.key_at:
            self._tap_key()
            self.cooldown_until = now + random.uniform(
                self.cfg.cooldown_min_s, self.cfg.cooldown_max_s,
            )
            self.state = self.COOLDOWN
            return True
        return False


class FrameRateLimiter:
    """Ограничивает цикл сверху до `fps` кадров в секунду."""

    def __init__(self, fps: int) -> None:
        self.frame_dt = 1.0 / max(1, fps)

    def sleep_to_frame(self, started_at: float) -> None:
        elapsed = time.perf_counter() - started_at
        remaining = self.frame_dt - elapsed
        if remaining > 0:
            time.sleep(remaining)


class FishingBot:
    """Главный оркестратор: захват → детект → humanizer → клавиши."""

    def __init__(self) -> None:
        self.screen = ScreenCapture()
        self.detector = BarDetector()
        self.humanizer = Humanizer(CONFIG.humanizer)
        self.keys = self._build_keys()
        self.reward = (
            RewardScreenWatcher(CONFIG.reward_screen)
            if CONFIG.reward_screen.enabled else None
        )
        self.prompt = (
            InteractPromptWatcher(CONFIG.interact_prompt)
            if CONFIG.interact_prompt.enabled else None
        )
        self.banner = (
            FishCaughtBannerWatcher(CONFIG.fish_caught_banner)
            if CONFIG.fish_caught_banner.enabled else None
        )
        self.logger = DebugLogger(0.1 if CONFIG.debug else 0.5)
        self.rate = FrameRateLimiter(CONFIG.fps)
        self.running = False
        self.quit = False

    @staticmethod
    def _build_keys() -> KeyHolder:
        if CONFIG.invert_keys:
            return KeyHolder(CONFIG.key_right, CONFIG.key_left)
        return KeyHolder(CONFIG.key_left, CONFIG.key_right)

    def toggle(self) -> None:
        self.running = not self.running
        if not self.running:
            self.keys.release_all()
            self.humanizer.reset()
        mode = "humanized" if CONFIG.humanizer.enabled else "raw"
        on_off = "ON " if self.running else "OFF"
        print(f"[bot] {on_off} ({mode}) (toggle {CONFIG.hotkey_toggle.upper()})")

    def stop(self) -> None:
        self.keys.release_all()
        self.humanizer.reset()
        self.running = False
        self.quit = True
        print("[bot] quit")

    def _step(self) -> FrameStats:
        img = self.screen.grab()
        det = self.detector.detect(img)
        slider_x = float(det.slider_x) if det.has_slider else None
        zone_center = float(det.zone_center) if det.has_zone else None
        action = self.humanizer.step(
            slider_x, zone_center,
            CONFIG.deadband_px, CONFIG.engage_threshold_px,
        )
        phys = self._apply_action(action)
        return FrameStats(det, action, phys)

    def _apply_action(self, action: str) -> str:
        if action == LEFT:
            self.keys.press_left()
            return "key_right(D)" if CONFIG.invert_keys else "key_left(A)"
        if action == RIGHT:
            self.keys.press_right()
            return "key_left(A)" if CONFIG.invert_keys else "key_right(D)"
        self.keys.release_all()
        return "—"

    def run(self) -> None:
        keyboard.add_hotkey(CONFIG.hotkey_toggle, self.toggle)
        keyboard.add_hotkey(CONFIG.hotkey_quit, self.stop)
        print(
            f"[bot] ready. {CONFIG.hotkey_toggle.upper()} = start/pause, "
            f"{CONFIG.hotkey_quit.upper()} = quit."
        )
        print(f"[bot] region: {self.screen.bbox}")

        try:
            while not self.quit:
                t0 = time.perf_counter()
                if self.running:
                    stats = self._step()
                    self.logger.maybe_log(t0, stats, self.keys.state)
                    if self.reward is not None and self.reward.tick(t0):
                        print(f"[bot] reward screen → {CONFIG.reward_screen.esc_key.upper()}")
                    if self.prompt is not None and self.prompt.tick(t0):
                        print(f"[bot] interact prompt → {CONFIG.interact_prompt.key.upper()}")
                    if self.banner is not None and self.banner.tick(t0):
                        print(f"[bot] fish caught banner → {CONFIG.fish_caught_banner.key.upper()}")
                else:
                    time.sleep(0.05)
                self.rate.sleep_to_frame(t0)
        finally:
            self.keys.release_all()


if __name__ == "__main__":
    FishingBot().run()
