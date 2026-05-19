import io
import sys


def ensure_utf8_stdout() -> None:
    """Принудительно переключает stdout на UTF-8, чтобы кириллица не падала на cp1251."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    elif isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
