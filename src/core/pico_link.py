"""Двусторонний канал с Pico через vendor-defined raw HID.

Pico экспонирует композитный USB: mouse + keyboard + vendor HID 64-байтный
канал (usage_page=0xFF00, usage=0x01). Этот класс ищет именно vendor-интерфейс
по VID/PID + usage_page и гоняет 64-байт IN/OUT репорты.

Формат репорта (обе стороны): [len:1][payload:63]. payload — ASCII команда,
остаток нулями.

TX: `send(line)` пишет OUT-репорт (host -> pico). Безопасно из любого потока.
RX: Pico шлёт IN-репорты `CTL <cmd>`; фоновый поток-читатель кладёт их в
очередь, главный цикл бота вычитывает через `pop()`.
"""
import queue
import threading

import hid


# (VID, PID) пары, по которым ищем vendor HID Pico.
# 2E8A:0005 — стоковый Raspberry Pi Pico, 258A:1006 — кастомная перепрошивка.
PICO_IDS = [(0x2E8A, 0x0005), (0x258A, 0x1006)]
VENDOR_USAGE_PAGE = 0xFF00
VENDOR_USAGE = 0x01
REPORT_LEN = 64
# Pico шлёт `CTL <op>` — префикс артефакт старого CDC-протокола, где он
# отделял команды от обычного print(). Стрипаем, чтобы runner получал
# op-имя в parts[0] (как было раньше через @CTL).
CTL_PREFIX = "CTL "


def find_pico_vendor_path() -> bytes | None:
    for vid, pid in PICO_IDS:
        for info in hid.enumerate(vid, pid):
            if (info.get("usage_page") == VENDOR_USAGE_PAGE
                    and info.get("usage") == VENDOR_USAGE):
                return info["path"]
    return None


def _pack_report(line: str) -> bytes:
    payload = line.encode("utf-8", errors="replace")[:REPORT_LEN - 1]
    n = len(payload)
    # [report_id=0][len][payload][padding] — всего REPORT_LEN + 1 байт.
    return bytes([0, n]) + payload + b"\x00" * (REPORT_LEN - 1 - n)


def _unpack_report(data) -> str | None:
    if not data or len(data) < 1:
        return None
    n = data[0]
    if n == 0 or n >= REPORT_LEN:
        return None
    return bytes(data[1:1 + n]).decode("utf-8", errors="replace")


class PicoLink:
    def __init__(self, path: bytes | None = None) -> None:
        self.path = path or find_pico_vendor_path()
        if not self.path:
            pairs = ", ".join(f"{v:04X}:{p:04X}" for v, p in PICO_IDS)
            raise RuntimeError(
                f"Pico vendor HID не найден (искал VID/PID: {pairs}, "
                f"usage_page=0x{VENDOR_USAGE_PAGE:04X})"
            )
        self._dev = hid.device()
        self._dev.open_path(self.path)
        self._dev.set_nonblocking(False)
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()
        self._write_lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    @property
    def port(self) -> str:
        # Совместимость с bot.py — раньше показывалось COM-имя; теперь путь HID.
        try:
            return self.path.decode("utf-8", errors="replace")
        except Exception:
            return "HID"

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            try:
                data = self._dev.read(REPORT_LEN, timeout_ms=200)
            except Exception:
                return
            if not data:
                continue
            line = _unpack_report(data)
            if not line:
                continue
            if line.startswith(CTL_PREFIX):
                line = line[len(CTL_PREFIX):]
            self._queue.put(line)

    def send(self, line: str) -> None:
        """Шлёт строку OUT-репортом. Безопасно из любого потока."""
        report = _pack_report(line)
        with self._write_lock:
            try:
                self._dev.write(report)
            except Exception:
                pass

    def pop(self) -> str | None:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def close(self) -> None:
        self._stop.set()
        try:
            self._dev.close()
        except Exception:
            pass
