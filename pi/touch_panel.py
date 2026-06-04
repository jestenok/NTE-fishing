"""4 тач-кнопки 2x2 в нижней половине LCD — управление ботом на хосте.

Каждый тап:
  1. Шлёт `CTL <cmd>` IN-репортом в VendorHID. Если хост HID не открыл —
     `is_open()` вернёт False и репорт пропускается. send_report сам не
     блокирует надолго, но лишний раз шуметь незачем.
  2. Эмитит `CTL <cmd>` в локальный dispatcher — Dashboard на Pico показывает.

Кнопки фиксированные:
  BTN1 RUN/STOP   -> CTL RUN
  BTN2 PROF       -> CTL PROF_NEXT
  BTN3 DBG        -> CTL DBG_NEXT
  BTN4 QUIT       -> CTL QUIT

Последняя нажатая кнопка подсвечивается зелёным фоном — визуальный фидбек.
"""
import time

# Подсветка кнопки гаснет, если за последние RELEASE_MS мс не было ни одного
# touch-события. Нужно потому что GT911 в континуальном режиме выставляет бит
# "data ready" не на каждый poll — между апдейтами read() возвращает (None,None,0)
# даже если палец на экране, и без debounce подсветка визуально мерцает.
RELEASE_MS = 150


class Button:
    def __init__(self, btn_id, x, y, w, h, label, cmd):
        self.id = btn_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.label = label
        self.cmd = cmd

    def contains(self, px, py):
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h


class TouchPanel:
    def __init__(self, screen, touch, dispatcher, vendor_hid=None):
        self._s = screen
        self._t = touch
        self._d = dispatcher
        self._hid = vendor_hid

        W = screen.width
        H = screen.half_height
        cw = W // 2
        ch = H // 2

        self._buttons = [
            Button(1, 0,  0,  cw, ch, "RUN/STOP", "RUN"),
            Button(2, cw, 0,  cw, ch, "PROF",     "PROF_NEXT"),
            Button(3, 0,  ch, cw, ch, "DBG",      "DBG_NEXT"),
            Button(4, cw, ch, cw, ch, "QUIT",     "QUIT"),
        ]
        self._H_top = H  # нижняя полоса начинается с физического y = H
        self._was_pressed = False
        self._last_pressed = None
        self._last_touch_ms = 0
        self._render()

    def poll(self):
        """Должен вызываться часто из главного цикла."""
        x, y, n = self._t.read()
        now = time.ticks_ms()
        if not n or x is None:
            self._was_pressed = False
            # палец отпущен → через RELEASE_MS без событий гасим подсветку
            if (self._last_pressed is not None
                and time.ticks_diff(now, self._last_touch_ms) > RELEASE_MS):
                self._last_pressed = None
                self._render()
            return
        self._last_touch_ms = now
        if self._was_pressed:
            return
        self._was_pressed = True
        if y < self._H_top:
            return
        local_y = y - self._H_top
        for btn in self._buttons:
            if btn.contains(x, local_y):
                self._last_pressed = btn.id
                self._render()
                if self._hid is not None and self._hid.is_open():
                    self._hid.send("CTL " + btn.cmd)
                self._d.dispatch("CTL " + btn.cmd)
                return

    def _render(self):
        s = self._s

        def draw(lcd):
            lcd.fill(s.BLACK)
            for btn in self._buttons:
                highlighted = (btn.id == self._last_pressed)
                if highlighted:
                    lcd.fill_rect(btn.x + 2, btn.y + 2,
                                  btn.w - 4, btn.h - 4, s.GREEN)
                    label_color = s.BLACK
                else:
                    lcd.rect(btn.x + 2, btn.y + 2,
                             btn.w - 4, btn.h - 4, s.WHITE)
                    label_color = s.WHITE
                tx = btn.x + max(0, (btn.w - len(btn.label) * 8) // 2)
                ty = btn.y + (btn.h - 8) // 2
                lcd.text(btn.label, tx, ty, label_color)

        s.draw_bottom(draw)
