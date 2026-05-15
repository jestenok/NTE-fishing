import time
from dataclasses import dataclass

import keyboard

from config import CONFIG
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
        action = self.humanizer.step(slider_x, zone_center, CONFIG.deadband_px)
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
                else:
                    time.sleep(0.05)
                self.rate.sleep_to_frame(t0)
        finally:
            self.keys.release_all()


if __name__ == "__main__":
    FishingBot().run()
