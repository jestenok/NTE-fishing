import time


class Countdown:
    """Печатает отсчёт N секунд. Возвращает False, если был Ctrl+C."""

    def __init__(self, seconds=5, printer=print, sleeper=time.sleep):
        self._seconds = seconds
        self._print = printer
        self._sleep = sleeper

    def wait(self):
        self._print("=" * 50)
        self._print("HID init in {} seconds. Ctrl+C to abort.".format(self._seconds))
        self._print("=" * 50)
        try:
            for i in range(self._seconds, 0, -1):
                self._print("  ...{}s".format(i))
                self._sleep(1)
            return True
        except KeyboardInterrupt:
            self._print(">>> aborted, REPL stays alive")
            return False
