"""Пьезо-бипер на GP13 (LAFVIN Pico Development Kit).

WIKI/драйвер LCD предупреждают: «GP13 — пьезо-бипер, НЕ трогать как PWM».
Значит модель активная (с встроенным генератором) — достаточно подать HIGH,
писк появляется сам.

Сделано неблокирующе: `beep(ms)` фиксит дедлайн отпускания, а реальное
снятие сигнала происходит в `tick()`, который дёргает главный цикл
(через HidReader.add_ticker). Таким образом писк не задерживает HID.
"""
from machine import Pin
import time

BEEP_PIN = 13


class Beeper:
    def __init__(self):
        self._pin = Pin(BEEP_PIN, Pin.OUT, value=0)
        self._off_at_ms = 0

    def beep(self, duration_ms=30):
        self._pin.value(1)
        self._off_at_ms = time.ticks_add(time.ticks_ms(), duration_ms)

    def beep_unknown(self):
        self.beep(40)

    def beep_error(self):
        self.beep(120)

    def tick(self):
        if self._off_at_ms and time.ticks_diff(time.ticks_ms(), self._off_at_ms) >= 0:
            self._pin.value(0)
            self._off_at_ms = 0
