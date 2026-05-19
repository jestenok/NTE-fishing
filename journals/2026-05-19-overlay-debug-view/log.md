# Задача: режим «оверлей» для debug_view (python)
Дата: 2026-05-19
Статус: в работе

## План
1. core/overlay_view.py — OverlayView: прозрачное layered-окно Win32 поверх
   игры, click-through (WS_EX_TRANSPARENT), без инъекции. tkinter + ctypes.
2. profiles/base.py — debug_view: bool | str (False / "window" / "overlay").
3. core/runner.py — фабрика _make_debug_view по режиму; обновить лог-сообщение.
4. Оба класса дают одинаковый интерфейс render(blocks)/close() + атрибут label.

## Прогресс
- Изучил debug_view.py, runner.py, module.py, base.py, capture.py, geometry.py.
  Интерфейс окна отладки: render(blocks: list[(name, bbox, ok)]), close().
  bbox — mss-словарь {left, top, width, height} в пикселях экрана.

## Решения и находки
- Оверлей: tkinter Tk(overrideredirect) + attributes(-transparentcolor) даёт
  color-key прозрачность; click-through добавляется через ctypes —
  WS_EX_LAYERED | WS_EX_TRANSPARENT на GetParent(winfo_id()).
- ctypes: обязательно restype=c_void_p у GetParent, иначе HWND усекается на x64.
- SetProcessDPIAware до создания Tk() — чтобы winfo_screenwidth = физические
  пиксели и совпадал с bbox от mss.

## Обнаруженные навыки
