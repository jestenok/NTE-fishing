import time
from dispatcher import DispatchListener

# X-граница левой статус-колонки. Правее — журнал нажатий тач-кнопок.
_SPLIT_X = 300
_RIGHT_X = _SPLIT_X + 8
_LEFT_MAX_CHARS = (_SPLIT_X - 12) // 8  # 8px на символ в framebuf.text


class Dashboard(DispatchListener):
    """Статус-панель в ВЕРХНЕЙ половине экрана (низ занят кнопками).

    Layout:
      слева  — счётчики/статус бота/последняя команда/ошибка.
      справа — журнал последних CTL-нажатий тач-кнопок (push при on_command).

    Throttle: не чаще, чем раз в `min_period_ms`, чтобы не тормозить HID.
    """

    MAX_PRESS_LOG = 7

    def __init__(self, screen, min_period_ms=500, beeper=None):
        self._s = screen
        self._period = min_period_ms
        self._start_ms = time.ticks_ms()
        self._last_render_ms = -1
        self._cmds = 0
        self._errors = 0
        self._unknown = 0
        self._last_cmd = "-"
        self._last_err = "-"
        self._bot_state = "?"
        self._bot_profile = "-"
        self._bot_debug = "-"
        self._press_log = []  # последние нажатия тача (RUN/PROF_NEXT/…)
        self._beeper = beeper
        self._render()

    def set_status(self, args):
        """args = [<ON|OFF>, <profile>, <debug>]; недостающие → '?'."""
        self._bot_state = args[0] if len(args) >= 1 else "?"
        self._bot_profile = args[1] if len(args) >= 2 else "-"
        self._bot_debug = args[2] if len(args) >= 3 else "-"
        self._last_render_ms = -1
        self._render()

    def on_command(self, name, args):
        if name == "STATUS":
            return  # уже отрисовано через set_status, в last не суём
        self._cmds += 1
        self._last_cmd = ("{} {}".format(name, " ".join(args))).strip()
        if name == "CTL" and args:
            self._push_press(args[0])
        self._maybe_render()

    def on_unknown(self, name):
        self._unknown += 1
        self._last_cmd = "? " + name
        if self._beeper:
            self._beeper.beep_unknown()
        self._maybe_render()

    def on_error(self, name, exc):
        self._errors += 1
        self._last_err = "{}: {}".format(name, exc)
        if self._beeper:
            self._beeper.beep_error()
        self._maybe_render()

    def force_refresh(self):
        self._last_render_ms = time.ticks_ms()
        self._render()

    def _push_press(self, cmd):
        self._press_log.append(cmd)
        if len(self._press_log) > self.MAX_PRESS_LOG:
            del self._press_log[0]

    def _maybe_render(self):
        now = time.ticks_ms()
        if self._last_render_ms < 0 or time.ticks_diff(now, self._last_render_ms) >= self._period:
            self._last_render_ms = now
            self._render()

    def _render(self):
        up = time.ticks_diff(time.ticks_ms(), self._start_ms) // 1000
        s = self._s
        left = [
            "Pico HID dashboard",
            "up:{}s cmds:{} err:{} unk:{}".format(
                up, self._cmds, self._errors, self._unknown),
            "last: " + self._truncate(self._last_cmd, _LEFT_MAX_CHARS - 6),
            "err : " + self._truncate(self._last_err, _LEFT_MAX_CHARS - 6),
            "",
            "bot : {} prof:{}".format(self._bot_state,
                                      self._truncate(self._bot_profile, 16)),
            "dbg : " + self._truncate(self._bot_debug, _LEFT_MAX_CHARS - 6),
        ]
        press = self._press_log  # снимок ссылки

        def draw(lcd):
            lcd.fill(s.BLACK)
            # левая колонка — статус
            for i, line in enumerate(left):
                lcd.text(line, 12, 10 + i * 16, s.WHITE)
            # разделитель
            lcd.vline(_SPLIT_X, 4, s.half_height - 8, s.WHITE)
            # правая колонка — лог нажатий
            lcd.text("presses:", _RIGHT_X, 10, s.GREEN)
            if not press:
                lcd.text("-", _RIGHT_X, 10 + 16, s.WHITE)
            else:
                for i, p in enumerate(press):
                    lcd.text(p, _RIGHT_X, 10 + (i + 1) * 16, s.WHITE)

        s.draw_top(draw)

    @staticmethod
    def _truncate(s, n):
        return s if len(s) <= n else s[: n - 1] + "~"
