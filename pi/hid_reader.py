import time


class HidReader:
    """Кооперативный цикл: VendorHID.recv() + список тикеров между чтениями.

    Тикеры (callable без аргументов) вызываются каждый круг, даже когда
    OUT-репортов от хоста нет. Используется чтобы вписать опрос тача без
    потери HID-команд.
    """

    def __init__(self, vendor_hid, dispatcher, poll_ms=2):
        self._hid = vendor_hid
        self._dispatcher = dispatcher
        self._poll_ms = poll_ms
        self._tickers = []

    def add_ticker(self, fn):
        self._tickers.append(fn)

    def run(self):
        while True:
            try:
                while True:
                    line = self._hid.recv()
                    if line is None:
                        break
                    line = line.strip()
                    if line:
                        self._dispatcher.dispatch(line)
                for fn in self._tickers:
                    fn()
                time.sleep_ms(self._poll_ms)
            except KeyboardInterrupt:
                return
