"""Кольцевой лог последних событий бота для окна отладки.

Источник пишет через `EVENT_LOG.push("F")`, окно отладки читает `recent()`
и рисует строки под индикатором BOT:ON/OFF. Новые события — в начале списка,
старые «уезжают» вниз и выпадают при переполнении.
"""
import time
from collections import deque
from threading import Lock

_MAX = 10


class EventLog:
    def __init__(self, maxlen: int = _MAX) -> None:
        self._buf: deque[tuple[float, str]] = deque(maxlen=maxlen)
        self._lock = Lock()

    def push(self, text: str) -> None:
        with self._lock:
            self._buf.appendleft((time.time(), text))

    def recent(self) -> list[tuple[float, str]]:
        with self._lock:
            return list(self._buf)


EVENT_LOG = EventLog()
