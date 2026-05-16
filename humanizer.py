import math
import random
import time
from collections import deque
from typing import Protocol

from config import HumanizerConfig

LEFT = "left"
RIGHT = "right"
RELEASE = "release"


def _opposite(d: str) -> str:
    if d == LEFT:
        return RIGHT
    if d == RIGHT:
        return LEFT
    return RELEASE


def _lognormal_ms(median_ms: float, sigma: float, lo_ms: float, hi_ms: float) -> float:
    raw = math.exp(random.gauss(math.log(max(1.0, median_ms)), sigma))
    return max(lo_ms, min(hi_ms, raw)) / 1000.0


class DecisionContext:
    """Контейнер на один шаг. Переиспользуется — `reset()` каждый кадр.

    Стейджи мутируют поля in-place. Если стейдж решает, что выходить раньше
    остальных, он вызывает `finish(action)` — пайплайн прекращает обход.
    """
    __slots__ = (
        "now",
        "slider_x", "zone_center", "deadband_px", "engage_threshold_px",
        "velocity", "predicted_x", "predicted_err",
        "desired", "actual", "duration",
        "committed_miss",
        "done", "result",
    )

    def __init__(self):
        self.now = 0.0
        self.slider_x: float | None = None
        self.zone_center: float | None = None
        self.deadband_px: int = 0
        self.engage_threshold_px: int = 0
        self.velocity = 0.0
        self.predicted_x = 0.0
        self.predicted_err = 0.0
        self.desired = RELEASE
        self.actual = RELEASE
        self.duration = 0.0
        self.committed_miss = False
        self.done = False
        self.result = RELEASE

    def reset(self, slider_x, zone_center, deadband_px, engage_threshold_px):
        self.now = time.perf_counter()
        self.slider_x = slider_x
        self.zone_center = zone_center
        self.deadband_px = deadband_px
        self.engage_threshold_px = engage_threshold_px
        self.velocity = 0.0
        self.predicted_x = slider_x if slider_x is not None else 0.0
        self.predicted_err = 0.0
        self.desired = RELEASE
        self.actual = RELEASE
        self.duration = 0.0
        self.committed_miss = False
        self.done = False
        self.result = RELEASE

    def finish(self, action: str) -> None:
        self.done = True
        self.result = action


class HumanizerState:
    """Долгоживущее состояние между вызовами `Humanizer.step()`."""
    __slots__ = (
        "current", "lock_until",
        "pending", "pending_commit_at", "pending_predicted_err",
        "pos_history",
        "session_start", "last_press_at",
        "miss_recovery_until", "post_miss_release_until", "in_miss_press",
    )

    def __init__(self):
        self.current: str = RELEASE
        self.lock_until: float = 0.0
        self.pending: str | None = None
        self.pending_commit_at: float = 0.0
        self.pending_predicted_err: float = 0.0
        self.pos_history: deque[tuple[float, float]] = deque(maxlen=16)
        self.session_start: float | None = None
        self.last_press_at: float = 0.0
        self.miss_recovery_until: float = 0.0
        self.post_miss_release_until: float = 0.0
        self.in_miss_press: bool = False

    def reset(self) -> None:
        self.current = RELEASE
        self.lock_until = 0.0
        self.pending = None
        self.pos_history.clear()
        self.last_press_at = 0.0
        self.miss_recovery_until = 0.0
        self.post_miss_release_until = 0.0
        self.in_miss_press = False


class Stage(Protocol):
    def apply(self, ctx: DecisionContext, state: HumanizerState) -> None: ...


class PerceptionStage:
    """История позиций ползунка и оценка скорости."""

    def __init__(self, cfg: HumanizerConfig):
        self.cfg = cfg

    def apply(self, ctx, state):
        if ctx.slider_x is not None:
            state.pos_history.append((ctx.now, ctx.slider_x))
        else:
            state.pos_history.clear()
        ctx.velocity = self._velocity(state, ctx.now)

    def _velocity(self, state, now):
        hist = state.pos_history
        if len(hist) < 2:
            return 0.0
        cutoff = now - self.cfg.velocity_window_s
        first_in_window = None
        for t, x in hist:
            if t >= cutoff:
                first_in_window = (t, x)
                break
        if first_in_window is None or first_in_window == hist[-1]:
            first_in_window = hist[-2]
        t0, x0 = first_in_window
        t1, x1 = hist[-1]
        dt = t1 - t0
        return (x1 - x0) / dt if dt > 1e-6 else 0.0


class LockGuardStage:
    """Удержание текущего нажатия, emergency-break, фаза post-miss-release."""

    def __init__(self, cfg: HumanizerConfig):
        self.cfg = cfg

    def apply(self, ctx, state):
        if ctx.now < state.lock_until:
            if state.in_miss_press:
                ctx.finish(state.current)
                return
            if self.cfg.use_emergency_break and self._should_break(ctx, state):
                state.lock_until = 0.0
                state.post_miss_release_until = 0.0
                state.pending = None
            else:
                ctx.finish(state.current)
                return
        else:
            state.in_miss_press = False

        if ctx.now < state.post_miss_release_until:
            state.current = RELEASE
            ctx.finish(RELEASE)

    def _should_break(self, ctx, state):
        if state.current not in (LEFT, RIGHT):
            return False
        if ctx.slider_x is None or ctx.zone_center is None:
            return True
        err = ctx.slider_x - ctx.zone_center
        if abs(err) <= ctx.deadband_px:
            return True  # догнали до центра — отпустить, не дожидая конца press_duration
        thr = self.cfg.emergency_break_px
        if state.current == LEFT and err < -thr:
            return True
        if state.current == RIGHT and err > thr:
            return True
        return False


class PredictionStage:
    """Антиципация по скорости + шум предсказания."""

    def __init__(self, cfg: HumanizerConfig):
        self.cfg = cfg

    def apply(self, ctx, state):
        if ctx.slider_x is None or ctx.zone_center is None:
            ctx.predicted_x = 0.0
            ctx.predicted_err = 0.0
            return
        x = ctx.slider_x
        if self.cfg.use_anticipation:
            x += ctx.velocity * self.cfg.anticipation_ms / 1000.0
        if self.cfg.use_prediction_noise:
            x += random.gauss(0.0, self.cfg.prediction_noise_px)
        ctx.predicted_x = x
        ctx.predicted_err = x - ctx.zone_center


class ClassifyStage:
    """predicted_err → desired с гистерезисом.

    Если бот сейчас стоит (`state.current == RELEASE`), снова чесаться он
    начинает только когда |err| превысил «внешний» порог `engage_threshold_px`.
    Если уже давит — отпускает при возврате в deadband. Это исключает
    мелкое дрожание, когда ползунок болтается вокруг центра.
    """

    def __init__(self, cfg: HumanizerConfig):
        self.cfg = cfg

    def apply(self, ctx, state):
        if ctx.slider_x is None or ctx.zone_center is None:
            ctx.desired = RELEASE
            return
        e = ctx.predicted_err
        threshold = ctx.engage_threshold_px if state.current == RELEASE else ctx.deadband_px
        if e > threshold:
            ctx.desired = LEFT
        elif e < -threshold:
            ctx.desired = RIGHT
        else:
            ctx.desired = RELEASE


class ReactionStage:
    """Pending-механика и реакционная задержка (опционально с jitter)."""

    def __init__(self, cfg: HumanizerConfig):
        self.cfg = cfg

    def apply(self, ctx, state):
        if ctx.desired == state.current:
            state.pending = None
            ctx.finish(state.current)
            return

        reversal = (
            state.current in (LEFT, RIGHT)
            and ctx.desired in (LEFT, RIGHT)
            and ctx.desired != state.current
        )
        continuation = (
            ctx.desired in (LEFT, RIGHT)
            and state.current == RELEASE
            and ctx.now - state.last_press_at < 0.4
        )

        if state.pending != ctx.desired:
            state.pending = ctx.desired
            state.pending_predicted_err = ctx.predicted_err
            median = self._median_ms(state, ctx.now, reversal, continuation)
            if self.cfg.use_rt_jitter:
                delay = _lognormal_ms(median, self.cfg.reaction_sigma,
                                      self.cfg.rt_min_ms, self.cfg.rt_max_ms)
            else:
                delay = median / 1000.0
            state.pending_commit_at = ctx.now + delay

        if ctx.now < state.pending_commit_at:
            ctx.finish(state.current)

    def _median_ms(self, state, now, reversal, continuation):
        median = self.cfg.reaction_median_ms

        if self.cfg.use_warmup or self.cfg.use_fatigue:
            if state.session_start is None:
                state.session_start = now
            elapsed = now - state.session_start
            if self.cfg.use_warmup:
                frac = max(0.0, 1.0 - elapsed / max(0.01, self.cfg.warmup_seconds))
                median += frac * self.cfg.warmup_extra_ms
            if self.cfg.use_fatigue:
                median += min(self.cfg.fatigue_cap_ms,
                              (elapsed / 60.0) * self.cfg.fatigue_ms_per_min)

        if self.cfg.use_reversal_penalty and reversal:
            median += self.cfg.reversal_penalty_ms
        if self.cfg.use_rhythm_bonus and continuation:
            median -= self.cfg.rhythm_bonus_ms
        if self.cfg.use_miss and now < state.miss_recovery_until:
            median += 60.0

        return max(30.0, median)


class CommitStage:
    """Финальное действие: промах / пауза / нормальное нажатие / релиз."""

    def __init__(self, cfg: HumanizerConfig):
        self.cfg = cfg

    def apply(self, ctx, state):
        if ctx.desired in (LEFT, RIGHT):
            actual, duration = self._commit_press(ctx, state)
        else:
            actual, duration = self._commit_release()

        state.current = actual
        state.lock_until = ctx.now + duration
        state.pending = None
        if actual in (LEFT, RIGHT):
            state.last_press_at = ctx.now

        if ctx.committed_miss:
            state.in_miss_press = True
            correction = random.uniform(
                self.cfg.miss_correction_min_ms,
                self.cfg.miss_correction_max_ms,
            ) / 1000.0
            state.post_miss_release_until = state.lock_until + correction
            state.pending = ctx.desired
            state.pending_commit_at = state.post_miss_release_until

        ctx.finish(actual)

    def _commit_press(self, ctx, state):
        err = state.pending_predicted_err
        roll = random.random()

        if self.cfg.use_miss and abs(err) <= self.cfg.miss_only_within_err_px \
                and roll < self.cfg.miss_chance:
            state.miss_recovery_until = ctx.now + self.cfg.miss_recovery_ms / 1000.0
            duration = _lognormal_ms(self.cfg.miss_median_ms, 0.25,
                                     self.cfg.miss_min_ms, self.cfg.miss_max_ms)
            ctx.committed_miss = True
            return _opposite(ctx.desired), duration

        if self.cfg.use_pause and abs(err) <= self.cfg.pause_only_within_err_px \
                and roll < self.cfg.pause_chance:
            duration = _lognormal_ms(self.cfg.pause_median_ms, 0.3, 20.0, 150.0)
            return RELEASE, duration

        if self.cfg.use_press_duration_scaling:
            median = self.cfg.press_base_ms + abs(err) * self.cfg.press_per_px_ms
            duration = _lognormal_ms(median, self.cfg.press_sigma,
                                     self.cfg.press_min_ms, self.cfg.press_max_ms)
        else:
            duration = self.cfg.press_base_ms / 1000.0
        return ctx.desired, duration

    def _commit_release(self):
        if self.cfg.use_rt_jitter:
            duration = _lognormal_ms(self.cfg.release_hold_median_ms, 0.25, 30.0, 220.0)
        else:
            duration = self.cfg.release_hold_median_ms / 1000.0
        return RELEASE, duration


class Humanizer:
    def __init__(self, cfg: HumanizerConfig):
        self.cfg = cfg
        self.state = HumanizerState()
        self._ctx = DecisionContext()
        self.stages: list[Stage] = [
            PerceptionStage(cfg),
            LockGuardStage(cfg),
            PredictionStage(cfg),
            ClassifyStage(cfg),
            ReactionStage(cfg),
            CommitStage(cfg),
        ]

    def reset(self) -> None:
        self.state.reset()

    def step(self, slider_x: float | None, zone_center: float | None,
             deadband_px: int, engage_threshold_px: int | None = None) -> str:
        engage = engage_threshold_px if engage_threshold_px is not None else deadband_px
        if not self.cfg.enabled:
            return self._raw(slider_x, zone_center, deadband_px, engage)

        ctx = self._ctx
        ctx.reset(slider_x, zone_center, deadband_px, engage)
        for stage in self.stages:
            stage.apply(ctx, self.state)
            if ctx.done:
                return ctx.result
        return ctx.result

    @staticmethod
    def _raw(slider_x, zone_center, deadband_px, _engage_threshold_px):
        if slider_x is None or zone_center is None:
            return RELEASE
        err = slider_x - zone_center
        if err > deadband_px:
            return LEFT
        if err < -deadband_px:
            return RIGHT
        return RELEASE
