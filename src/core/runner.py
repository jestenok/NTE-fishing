import time

import keyboard

from profiles.base import GameProfile


def _make_debug_view(mode: bool | str):
    """Создаёт окно отладки по режиму из профиля (None — отладка выключена).

    False/None — выкл; True или "window" — отдельное окно OpenCV;
    "overlay" — прозрачный оверлей поверх игры.
    """
    if not mode:
        return None
    if mode is True or mode == "window":
        from core.debug_view import DebugView
        return DebugView()
    if mode == "overlay":
        from core.overlay_view import OverlayView
        return OverlayView()
    raise SystemExit(
        f"неизвестный режим debug_view: {mode!r} "
        f"(ожидается False, 'window' или 'overlay')"
    )


class FrameRateLimiter:
    """Ограничивает цикл сверху до `fps` кадров в секунду."""

    def __init__(self, fps: int) -> None:
        self.frame_dt = 1.0 / max(1, fps)

    def sleep_to_frame(self, started_at: float) -> None:
        remaining = self.frame_dt - (time.perf_counter() - started_at)
        if remaining > 0:
            time.sleep(remaining)


class GameBot:
    """Главный оркестратор: крутит модули профиля кадр за кадром.

    Бот ничего не знает про конкретную игру — вся специфика в профиле и его
    модулях. F8 — старт/пауза, F9 — выход.
    """

    def __init__(self, profile: GameProfile) -> None:
        self.profile = profile
        self.modules = profile.build_modules()
        self.rate = FrameRateLimiter(profile.fps)
        self._debug_view = _make_debug_view(profile.debug_view)
        self.running = False
        self.quit = False

    def toggle(self) -> None:
        self.running = not self.running
        if not self.running:
            for m in self.modules:
                m.on_stop()
        state = "ON " if self.running else "OFF"
        print(f"[bot] {state} профиль={self.profile.name} "
              f"(toggle {self.profile.hotkey_toggle.upper()})")

    def stop(self) -> None:
        for m in self.modules:
            m.on_stop()
        self.running = False
        self.quit = True
        print("[bot] quit")

    def _render_debug(self) -> None:
        blocks = [(m.name, *m.debug_block()) for m in self.modules]
        self._debug_view.render(blocks)

    def run(self) -> None:
        keyboard.add_hotkey(self.profile.hotkey_toggle, self.toggle)
        keyboard.add_hotkey(self.profile.hotkey_quit, self.stop)
        names = ", ".join(m.name for m in self.modules)
        print(f"[bot] профиль '{self.profile.name}' загружен. модули: {names}")
        print(f"[bot] {self.profile.hotkey_toggle.upper()} = старт/пауза, "
              f"{self.profile.hotkey_quit.upper()} = выход.")
        if self._debug_view is not None:
            print("[bot] окно отладки ВКЛ (отдельное окно, не оверлей поверх игры)")
        try:
            while not self.quit:
                t0 = time.perf_counter()
                if self.running:
                    for m in self.modules:
                        msg = m.tick(t0)
                        if msg:
                            print(f"[{m.name}] {msg}")
                    if self._debug_view is not None:
                        self._render_debug()
                else:
                    time.sleep(0.05)
                self.rate.sleep_to_frame(t0)
        finally:
            for m in self.modules:
                m.on_stop()
            if self._debug_view is not None:
                self._debug_view.close()
