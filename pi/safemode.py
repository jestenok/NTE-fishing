import os


class SafeMode:
    def __init__(self, path="/.safemode"):
        self._path = path

    def is_active(self):
        try:
            os.stat(self._path)
            return True
        except OSError:
            return False
