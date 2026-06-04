import sys


class SerialReader:
    def __init__(self, dispatcher, stream=None):
        self._dispatcher = dispatcher
        self._stream = stream or sys.stdin

    def run(self):
        while True:
            try:
                line = self._stream.readline()
            except KeyboardInterrupt:
                return
            line = line.strip()
            if not line:
                continue
            self._dispatcher.dispatch(line)
