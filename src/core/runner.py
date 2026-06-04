import time

import keyboard

from profiles.base import DebugView, GameProfile, discover_profiles, load_profile


def _make_debug_view(mode: DebugView):
    if mode is DebugView.OFF:
        return None
    if mode is DebugView.WINDOW:
        from core.debug_view import DebugView as DebugWindow
        return DebugWindow()
    if mode is DebugView.OVERLAY:
        from core.overlay_view import OverlayView
        return OverlayView()
    raise SystemExit(f"неизвестный режим debug_view: {mode!r}")


_DEBUG_CYCLE = [DebugView.OFF, DebugView.WINDOW, DebugView.OVERLAY]


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

    Профиль и debug_view меняются на ходу через set_profile/set_debug_view.
    F8/F9 — старт-пауза/выход. Команды от Pico приходят через `pico_link`.
    """

    def __init__(self, profile: GameProfile, pico_link=None) -> None:
        self.profile = profile
        self.modules = profile.build_modules()
        self.rate = FrameRateLimiter(profile.fps)
        self._debug_view = _make_debug_view(profile.debug_view)
        self.running = False
        self.quit = False
        self._pico = pico_link

    def toggle(self) -> None:
        self.running = not self.running
        if not self.running:
            for m in self.modules:
                m.on_stop()
        state = "ON " if self.running else "OFF"
        print(f"[bot] {state} профиль={self.profile.name} "
              f"(toggle {self.profile.hotkey_toggle.upper()})")
        self._emit_status()

    def stop(self) -> None:
        for m in self.modules:
            m.on_stop()
        self.running = False
        self.quit = True
        print("[bot] quit")
        self._emit_status()

    def set_profile(self, name: str) -> None:
        if name == self.profile.name:
            print(f"[bot] профиль уже {name}, пропускаю")
            return
        for m in self.modules:
            m.on_stop()
        try:
            new_profile = load_profile(name)
        except SystemExit as e:
            print(f"[bot] не удалось сменить профиль: {e}")
            return
        self.profile = new_profile
        self.modules = new_profile.build_modules()
        self.rate = FrameRateLimiter(new_profile.fps)
        self.running = False
        print(f"[bot] профиль -> {name} (OFF)")
        self._emit_status()

    def cycle_profile(self) -> None:
        names = discover_profiles()
        if not names:
            return
        try:
            i = names.index(self.profile.name)
        except ValueError:
            i = -1
        self.set_profile(names[(i + 1) % len(names)])

    def set_debug_view(self, mode: DebugView) -> None:
        if self._debug_view is not None:
            self._debug_view.close()
        self._debug_view = _make_debug_view(mode)
        self.profile.debug_view = mode
        print(f"[bot] debug_view -> {mode.value}")
        self._emit_status()

    def _emit_status(self) -> None:
        if not self._pico:
            return
        state = "ON" if self.running else "OFF"
        self._pico.send(
            f"STATUS {state} {self.profile.name} {self.profile.debug_view.value}"
        )

    def cycle_debug_view(self) -> None:
        try:
            i = _DEBUG_CYCLE.index(self.profile.debug_view)
        except ValueError:
            i = -1
        self.set_debug_view(_DEBUG_CYCLE[(i + 1) % len(_DEBUG_CYCLE)])

    def _render_debug(self) -> None:
        blocks = [(m.name, *m.debug_block()) for m in self.modules]
        self._debug_view.render(blocks, self.running)

    def _pump_pico(self) -> None:
        if not self._pico:
            return
        while True:
            cmd = self._pico.pop()
            if cmd is None:
                return
            self._apply_pico_cmd(cmd)

    def _apply_pico_cmd(self, cmd: str) -> None:
        parts = cmd.split()
        if not parts:
            return
        op = parts[0].upper()
        if op == "RUN":
            self.toggle()
        elif op == "QUIT":
            self.stop()
        elif op == "PROF_NEXT":
            self.cycle_profile()
        elif op == "DBG_NEXT":
            self.cycle_debug_view()
        else:
            print(f"[bot] unknown pico cmd: {cmd}")

    def run(self) -> None:
        keyboard.add_hotkey(self.profile.hotkey_toggle, self.toggle)
        keyboard.add_hotkey(self.profile.hotkey_quit, self.stop)
        names = ", ".join(m.name for m in self.modules)
        print(f"[bot] профиль '{self.profile.name}' загружен. модули: {names}")
        print(f"[bot] {self.profile.hotkey_toggle.upper()} = старт/пауза, "
              f"{self.profile.hotkey_quit.upper()} = выход.")
        if self._debug_view is not None:
            print(f"[bot] окно отладки ВКЛ ({self.profile.debug_view.value})")
        if self._pico:
            print(f"[bot] Pico-link ВКЛ ({self._pico.port})")
            self._emit_status()
        try:
            while not self.quit:
                t0 = time.perf_counter()
                self._pump_pico()
                if self.running:
                    for m in self.modules:
                        msg = m.tick(t0)
                        if msg:
                            print(f"[{m.name}] {msg}")
                if self._debug_view is not None:
                    self._render_debug()
                if not self.running:
                    time.sleep(0.05)
                self.rate.sleep_to_frame(t0)
        finally:
            for m in self.modules:
                m.on_stop()
            if self._debug_view is not None:
                self._debug_view.close()
            if self._pico is not None:
                self._pico.close()
