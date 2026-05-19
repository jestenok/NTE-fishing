"""Окно отладки — режим «оверлей»: прозрачное окно поверх игры.

В отличие от DebugView (отдельное окно OpenCV со снимком экрана), этот режим
рисует рамки регионов ПРЯМО поверх игры. Это обычный прозрачный layered-window
Windows — НЕ инъекция в процесс игры и НЕ перехват её рендера: бот создаёт своё
верхнеуровневое окно, делает фон прозрачным (color-key) и сквозным для мыши
(WS_EX_TRANSPARENT — клики уходят в игру под оверлеем). Для системы это обычное
окно приложения.

Реализовано на стандартном tkinter + ctypes — без сторонних зависимостей.
Включается в профиле: GameProfile.debug_view = "overlay".
"""
import time
import tkinter as tk

try:
    import ctypes
    _user32 = ctypes.windll.user32
except (AttributeError, OSError):  # не Windows — оверлей недоступен
    _user32 = None

_OK_COLOR = "#00dc00"      # зелёный — объект задетектен
_MISS_COLOR = "#dc0000"    # красный — не задетектен
_TRANSPARENT = "#010101"   # цвет-ключ: пиксели этого цвета становятся прозрачными
_FPS = 15                  # частота перерисовки оверлея (бот крутится быстрее)

# Win32-константы для click-through layered-окна
_GWL_EXSTYLE = -20
_WS_EX_LAYERED = 0x00080000
_WS_EX_TRANSPARENT = 0x00000020

if _user32 is not None:
    # restype/argtypes обязательны: иначе HWND усекается до 32 бит на x64
    _user32.GetParent.restype = ctypes.c_void_p
    _user32.GetParent.argtypes = [ctypes.c_void_p]
    _user32.GetWindowLongW.restype = ctypes.c_long
    _user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    _user32.SetWindowLongW.restype = ctypes.c_long
    _user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]


class OverlayView:
    """Прозрачный оверлей поверх игры с рамками регионов модулей.

    Интерфейс совпадает с DebugView: render(blocks) и close().
    """

    label = "прозрачный оверлей поверх игры (layered-окно, без инъекции)"

    def __init__(self) -> None:
        self._interval = 1.0 / _FPS
        self._last = 0.0
        self._root: tk.Tk | None = None
        self._canvas: tk.Canvas | None = None

    def render(self, blocks: list[tuple[str, dict, bool]], running: bool) -> None:
        """blocks: список (имя модуля, bbox-словарь mss, флаг детекции)."""
        now = time.perf_counter()
        if now - self._last < self._interval:
            return
        self._last = now
        if self._root is None:
            self._build()
        self._canvas.delete("all")
        self._draw_status(running)
        for name, bbox, ok in blocks:
            self._draw_block(name, bbox, ok)
        try:
            self._root.update()
        except tk.TclError:
            self._root = self._canvas = None  # окно уничтожено — пересоздадим

    def _draw_status(self, running: bool) -> None:
        text = "BOT: ON" if running else "BOT: OFF"
        color = _OK_COLOR if running else _MISS_COLOR
        self._canvas.create_text(12, 12, text=text, fill=color,
                                 anchor="nw", font=("Segoe UI", 14, "bold"))

    def _draw_block(self, name: str, bbox: dict, ok: bool) -> None:
        color = _OK_COLOR if ok else _MISS_COLOR
        x, y = bbox["left"], bbox["top"]
        w, h = bbox["width"], bbox["height"]
        # только контур, без заливки — игра внутри рамки остаётся видимой
        self._canvas.create_rectangle(x, y, x + w, y + h, outline=color, width=2)
        label = f"{name}: {'DETECTED' if ok else '---'}"
        self._canvas.create_text(x + 4, max(y - 6, 12), text=label, fill=color,
                                 anchor="sw", font=("Segoe UI", 11, "bold"))

    def _build(self) -> None:
        """Создаёт полноэкранное прозрачное окно поверх всего."""
        if _user32 is not None:
            # пиксели окна = физические пиксели экрана (совпадение с bbox от mss)
            _user32.SetProcessDPIAware()
        root = tk.Tk()
        root.overrideredirect(True)                          # без рамки/заголовка
        root.attributes("-topmost", True)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{sw}x{sh}+0+0")
        root.configure(bg=_TRANSPARENT)
        root.attributes("-transparentcolor", _TRANSPARENT)   # фон → прозрачный
        canvas = tk.Canvas(root, bg=_TRANSPARENT, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        root.update_idletasks()
        root.lift()
        self._make_click_through(root)
        self._root, self._canvas = root, canvas

    @staticmethod
    def _make_click_through(root: tk.Tk) -> None:
        """Делает окно сквозным для мыши — клики проходят в игру под оверлеем."""
        if _user32 is None:
            return
        hwnd = _user32.GetParent(root.winfo_id())
        style = _user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        _user32.SetWindowLongW(hwnd, _GWL_EXSTYLE,
                               style | _WS_EX_LAYERED | _WS_EX_TRANSPARENT)

    def close(self) -> None:
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = self._canvas = None
