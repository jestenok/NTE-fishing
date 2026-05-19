from dataclasses import dataclass


@dataclass
class Region:
    """Прямоугольная область экрана в долях (0.0–1.0) от размера экрана.

    Доли, а не пиксели — чтобы регион не зависел от разрешения монитора.
    (x1, y1) — левый верхний угол, (x2, y2) — правый нижний.
    """
    x1: float
    y1: float
    x2: float
    y2: float

    def to_pixels(self, screen_w: int, screen_h: int) -> tuple[int, int, int, int]:
        """Возвращает (left, top, width, height) в пикселях для данного экрана."""
        left = int(self.x1 * screen_w)
        top = int(self.y1 * screen_h)
        right = int(self.x2 * screen_w)
        bottom = int(self.y2 * screen_h)
        return left, top, right - left, bottom - top
