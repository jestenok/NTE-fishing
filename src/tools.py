"""
Единый GUI-инструмент для подготовки профилей:
  • Pick color       — пипетка цвета, накопление HSVRange (бывший pick_color.py)
  • Measure region   — две точки курсора → Region (бывший measure.py)
  • Calibrate slider — снимок экрана + детектор полосы (бывший calibrate.py)

  python tools.py

Окно с кнопками. Запустил режим — переключайся в игру:
F7 — действие (проба / точка), F9 — стоп. Для калибровки указывается профиль
из выпадающего списка и задержка перед снимком.
"""
import ctypes
import ctypes.wintypes
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import cv2
import keyboard
import mss
import numpy as np

from core.capture import ScreenCapture
from core.hsv import mask_one
from core.io_utils import ensure_utf8_stdout
from mechanics.slider import BarDetector, SliderConfig, annotate
from profiles.base import GameProfile, load_profile
from profiles.cigame import PROFILE

ensure_utf8_stdout()

_PATCH = 11  # сторона квадрата-пробы для пипетки, пикселей


def _cursor_pos() -> tuple[int, int]:
    """Абсолютные координаты курсора мыши через WinAPI."""
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _list_profiles() -> list[str]:
    """Имена доступных профилей (файлы profiles/*.py кроме служебных)."""
    profiles_dir = Path(__file__).parent / "profiles"
    return sorted(
        p.stem for p in profiles_dir.glob("*.py")
        if p.stem not in ("__init__", "base")
    )


class ToolsApp:
    """Главное окно. Один фоновый поток за раз — режим pick/measure/calibrate."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("vision-bot tools")
        self.root.geometry("620x460")

        self._msg_q: queue.Queue[str] = queue.Queue()
        self._stop_evt = threading.Event()
        self._worker: threading.Thread | None = None

        self._build_ui()
        self.root.after(100, self._pump)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=(10, 10, 10, 4))
        top.pack(side=tk.TOP, fill=tk.X)

        self.btn_pick = ttk.Button(top, text="Pick color", width=18, command=self._start_pick)
        self.btn_measure = ttk.Button(top, text="Measure region", width=18, command=self._start_measure)
        self.btn_calib = ttk.Button(top, text="Calibrate slider", width=18, command=self._start_calibrate)
        self.btn_stop = ttk.Button(top, text="Stop", width=8, command=self._stop_current, state=tk.DISABLED)
        self.btn_pick.pack(side=tk.LEFT, padx=4)
        self.btn_measure.pack(side=tk.LEFT, padx=4)
        self.btn_calib.pack(side=tk.LEFT, padx=4)
        self.btn_stop.pack(side=tk.LEFT, padx=12)

        opts = ttk.Frame(self.root, padding=(10, 0, 10, 0))
        opts.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(opts, text="profile:").pack(side=tk.LEFT)
        self.profile_var = tk.StringVar(value=PROFILE)
        self.profile_cb = ttk.Combobox(
            opts, textvariable=self.profile_var,
            values=_list_profiles(), width=22, state="readonly",
        )
        self.profile_cb.pack(side=tk.LEFT, padx=6)
        ttk.Label(opts, text="delay (s):").pack(side=tk.LEFT, padx=(12, 0))
        self.delay_var = tk.StringVar(value="5")
        self.delay_sb = ttk.Spinbox(
            opts, from_=0, to=60, increment=1, width=4, textvariable=self.delay_var,
        )
        self.delay_sb.pack(side=tk.LEFT, padx=6)
        ttk.Label(opts, text="(только для Calibrate)").pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="режим: idle")
        ttk.Label(self.root, textvariable=self.status_var, padding=(10, 6)).pack(side=tk.TOP, anchor=tk.W)

        body = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.log = tk.Text(
            body, height=14, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10),
        )
        scroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # ---------- queue / worker plumbing ----------

    def _print(self, msg: str = "") -> None:
        """Печать из любого потока — попадает в Text через очередь и _pump."""
        self._msg_q.put(msg + "\n")

    def _pump(self) -> None:
        try:
            while True:
                msg = self._msg_q.get_nowait()
                self.log.configure(state=tk.NORMAL)
                self.log.insert(tk.END, msg)
                self.log.see(tk.END)
                self.log.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        if self._worker is not None and not self._worker.is_alive():
            self._worker = None
            self._set_mode("idle")
            self._append_separator()
        self.root.after(100, self._pump)

    def _append_separator(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, "--- готово ---\n\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_mode(self, name: str) -> None:
        self.status_var.set(f"режим: {name}")
        busy = name != "idle"
        new_state = tk.DISABLED if busy else tk.NORMAL
        for b in (self.btn_pick, self.btn_measure, self.btn_calib):
            b.configure(state=new_state)
        self.btn_stop.configure(state=tk.NORMAL if busy else tk.DISABLED)

    def _start(self, name: str, target) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_evt.clear()
        self._set_mode(name)
        self._worker = threading.Thread(
            target=self._run_worker, args=(target,), daemon=True,
        )
        self._worker.start()

    def _run_worker(self, target) -> None:
        try:
            target()
        except Exception as exc:  # noqa: BLE001
            self._print(f"ошибка: {exc!r}")
        finally:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass

    def _stop_current(self) -> None:
        self._stop_evt.set()

    def _on_close(self) -> None:
        self._stop_evt.set()
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.root.destroy()

    # ---------- режим: pick_color ----------

    def _start_pick(self) -> None:
        self._print("== Pick color ==")
        self._print(f"Патч {_PATCH}x{_PATCH} px вокруг курсора. F7 — проба, F9 — стоп.")
        self._start("pick_color", self._pick_loop)

    def _pick_loop(self) -> None:
        sct = mss.MSS()
        mon = sct.monitors[1]
        half = _PATCH // 2
        lo: np.ndarray | None = None
        hi: np.ndarray | None = None

        def sample() -> None:
            nonlocal lo, hi
            x, y = _cursor_pos()
            left = min(max(x - half, 0), mon["width"] - _PATCH)
            top = min(max(y - half, 0), mon["height"] - _PATCH)
            bbox = {"left": left, "top": top, "width": _PATCH, "height": _PATCH}
            bgr = cv2.cvtColor(np.asarray(sct.grab(bbox)), cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).reshape(-1, 3)
            p_lo = hsv.min(axis=0)
            p_hi = hsv.max(axis=0)
            mean = hsv.mean(axis=0).round().astype(int)
            lo = p_lo if lo is None else np.minimum(lo, p_lo)
            hi = p_hi if hi is None else np.maximum(hi, p_hi)
            rng = [int(v) for v in (*lo, *hi)]
            self._print(f"проба ({x}, {y}): mean H={mean[0]} S={mean[1]} V={mean[2]}")
            self._print(
                f"  в пробе: H {p_lo[0]}..{p_hi[0]}  "
                f"S {p_lo[1]}..{p_hi[1]}  V {p_lo[2]}..{p_hi[2]}"
            )
            self._print(
                f"  по всем пробам → HSVRange({rng[0]}, {rng[1]}, {rng[2]}, "
                f"{rng[3]}, {rng[4]}, {rng[5]})"
            )

        keyboard.add_hotkey("f7", sample)
        keyboard.add_hotkey("f9", self._stop_evt.set)
        while not self._stop_evt.is_set():
            time.sleep(0.05)

    # ---------- режим: measure ----------

    def _start_measure(self) -> None:
        self._print("== Measure region ==")
        self._print("F7 — точка под курсором (нужно две: ЛВ и ПН угол). F9 — отмена.")
        self._start("measure", self._measure_loop)

    def _measure_loop(self) -> None:
        sct = mss.MSS()
        mon = sct.monitors[1]
        screen_w, screen_h = mon["width"], mon["height"]
        mon_left, mon_top = mon["left"], mon["top"]
        self._print(f"screen: {screen_w}x{screen_h}")
        self._print("Наведи курсор на ЛЕВЫЙ-ВЕРХНИЙ угол и нажми F7.")

        points: list[tuple[float, float]] = []

        def capture() -> None:
            x, y = _cursor_pos()
            fx = (x - mon_left) / screen_w
            fy = (y - mon_top) / screen_h
            points.append((fx, fy))
            corner = "левый-верхний" if len(points) == 1 else "правый-нижний"
            self._print(
                f"  точка {len(points)} ({corner}): "
                f"pixel=({x}, {y})  доля=({fx:.3f}, {fy:.3f})"
            )
            if len(points) == 1:
                self._print("Теперь правый-нижний угол → F7.")
            else:
                self._stop_evt.set()

        keyboard.add_hotkey("f7", capture)
        keyboard.add_hotkey("f9", self._stop_evt.set)
        while not self._stop_evt.is_set():
            time.sleep(0.05)

        if len(points) < 2:
            self._print(f"Отмена (точек: {len(points)}).")
            return

        (ax, ay), (bx, by) = points
        x1, x2 = sorted((ax, bx))
        y1, y2 = sorted((ay, by))
        self._print("")
        self._print("Готовая область для config.Region:")
        self._print(f"    x1: float = {x1:.3f}")
        self._print(f"    y1: float = {y1:.3f}")
        self._print(f"    x2: float = {x2:.3f}")
        self._print(f"    y2: float = {y2:.3f}")
        self._print(f"  → Region(x1={x1:.3f}, y1={y1:.3f}, x2={x2:.3f}, y2={y2:.3f})")

    # ---------- режим: calibrate ----------

    def _start_calibrate(self) -> None:
        try:
            delay = max(0.0, float(self.delay_var.get()))
        except ValueError:
            self._print("delay должен быть числом")
            return
        profile_name = self.profile_var.get().strip()
        if not profile_name:
            self._print("выбери профиль")
            return
        self._print(f"== Calibrate slider (profile={profile_name}, delay={delay:.0f}) ==")
        self._start("calibrate", lambda: self._calibrate_loop(profile_name, delay))

    def _calibrate_loop(self, profile_name: str, delay: float) -> None:
        try:
            profile = load_profile(profile_name)
        except SystemExit as exc:
            self._print(str(exc))
            return
        slider = self._find_slider(profile)
        if slider is None:
            self._print(f"в профиле '{profile.name}' нет слайдер-механики")
            return
        cap = ScreenCapture(slider.region)
        self._print(f"screen: {cap.screen_w}x{cap.screen_h}")
        self._print(f"region: {cap.bbox}")

        remaining = int(delay)
        if remaining > 0:
            self._print(f"Переключайся в игру. Снимок через {remaining} сек:")
            while remaining > 0:
                self._print(f"  {remaining}...")
                if self._stop_evt.wait(timeout=1.0):
                    self._print("отмена")
                    return
                remaining -= 1

        frame = cap.grab()
        self._process_frame(frame, slider)

    @staticmethod
    def _find_slider(profile: GameProfile) -> SliderConfig | None:
        for module in profile.modules:
            if isinstance(module, SliderConfig):
                return module
        return None

    def _process_frame(self, img_bgr: np.ndarray, slider: SliderConfig) -> None:
        det = BarDetector(slider).detect(img_bgr)
        self._print(f"zone:   x1={det.zone_x1} x2={det.zone_x2} center={det.zone_center}")
        self._print(f"slider: x={det.slider_x}")
        if det.has_zone and det.has_slider:
            err = det.slider_x - det.zone_center
            key_a = slider.key_right if slider.invert_keys else slider.key_left
            key_d = slider.key_left if slider.invert_keys else slider.key_right
            self._print(
                f"err:    {err:+d} px (>0 → нажать {key_a.upper()}, "
                f"<0 → нажать {key_d.upper()})"
            )
        Path("images").mkdir(exist_ok=True)
        for name, img in (
            ("images/debug_input.png", img_bgr),
            ("images/debug_zone.png", mask_one(img_bgr, slider.zone_hsv)),
            ("images/debug_slider.png", mask_one(img_bgr, slider.slider_hsv)),
            ("images/debug_overlay.png", annotate(img_bgr, det)),
        ):
            cv2.imwrite(name, img)
            self._print(f"  saved {name}  ({img.shape[1]}x{img.shape[0]})")


def main() -> None:
    root = tk.Tk()
    ToolsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
