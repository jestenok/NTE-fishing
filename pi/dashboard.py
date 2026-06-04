import time
from dispatcher import DispatchListener


class Dashboard(DispatchListener):
    """Статус-панель на экране. Дёшево копит счётчики и редко перерисовывает.

    Throttle: не чаще, чем раз в `min_period_ms`, чтобы не тормозить HID.
    Верх экрана — статичный заголовок (рисуется один раз).
    Низ — динамика: счётчики и последняя команда/ошибка.
    """

    def __init__(self, screen, min_period_ms=500):
        self._s = screen
        self._period = min_period_ms
        self._start_ms = time.ticks_ms()
        self._last_render_ms = -1
        self._cmds = 0
        self._errors = 0
        self._unknown = 0
        self._last_cmd = "-"
        self._last_err = "-"

        self._render_header()
        self._render_body()

    def on_command(self, name, args):
        self._cmds += 1
        self._last_cmd = ("{} {}".format(name, " ".join(args))).strip()
        self._maybe_render()

    def on_unknown(self, name):
        self._unknown += 1
        self._last_cmd = "? " + name
        self._maybe_render()

    def on_error(self, name, exc):
        self._errors += 1
        self._last_err = "{}: {}".format(name, exc)
        self._maybe_render()

    def force_refresh(self):
        self._last_render_ms = time.ticks_ms()
        self._render_body()

    def _maybe_render(self):
        now = time.ticks_ms()
        if self._last_render_ms < 0 or time.ticks_diff(now, self._last_render_ms) >= self._period:
            self._last_render_ms = now
            self._render_body()

    def _render_header(self):
        s = self._s
        s.status_top([
            "Pico HID dashboard",
            "",
            "M dx dy   - move",
            "L R X     - clicks",
            "K spec    - keys",
        ], color=s.WHITE)

    def _render_body(self):
        up = time.ticks_diff(time.ticks_ms(), self._start_ms) // 1000
        s = self._s
        s.status_bottom([
            "up:{}s cmds:{} err:{}".format(up, self._cmds, self._errors),
            "unknown: {}".format(self._unknown),
            "",
            "last: " + self._truncate(self._last_cmd, 32),
            "err : " + self._truncate(self._last_err, 32),
        ], color=s.GREEN)

    @staticmethod
    def _truncate(s, n):
        return s if len(s) <= n else s[: n - 1] + "~"
