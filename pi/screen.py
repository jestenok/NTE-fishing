class Screen:
    """Высокоуровневая обёртка над LAFVIN_LCD.

    Буфер драйвера — половина экрана (480x160). Поэтому Screen
    хранит две независимые «полосы» (top / bottom) и обновляет каждую
    своей командой драйвера.
    """

    def __init__(self, lcd_factory=None):
        if lcd_factory is None:
            from LAFVIN_LCD import LCD_3inch5
            lcd_factory = LCD_3inch5
        self._lcd = lcd_factory()
        self._w = self._lcd.width
        self._h = self._lcd.height
        self.WHITE = self._lcd.WHITE
        self.BLACK = self._lcd.BLACK
        self.RED   = self._lcd.RED
        self.GREEN = self._lcd.GREEN
        self.BLUE  = self._lcd.BLUE

    @property
    def width(self):
        return self._w

    @property
    def half_height(self):
        return self._h

    def draw_top(self, render_fn):
        render_fn(self._lcd)
        self._lcd.show_up()

    def draw_bottom(self, render_fn):
        render_fn(self._lcd)
        self._lcd.show_down()

    def clear(self):
        self.draw_top(lambda lcd: lcd.fill(self.BLACK))
        self.draw_bottom(lambda lcd: lcd.fill(self.BLACK))

    def splash(self, title, subtitle=""):
        def top(lcd):
            lcd.fill(self.BLACK)
            lcd.fill_rect(0, 0, self._w, 30, self.BLUE)
            lcd.text(title, 12, 10, self.WHITE)
            if subtitle:
                lcd.text(subtitle, 12, 50, self.GREEN)
        self.draw_top(top)
        self.draw_bottom(lambda lcd: lcd.fill(self.BLACK))

    def status_top(self, lines, color=None):
        c = self.WHITE if color is None else color
        def render(lcd):
            lcd.fill(self.BLACK)
            for i, line in enumerate(lines):
                lcd.text(line, 12, 10 + i * 16, c)
        self.draw_top(render)

    def status_bottom(self, lines, color=None):
        c = self.WHITE if color is None else color
        def render(lcd):
            lcd.fill(self.BLACK)
            for i, line in enumerate(lines):
                lcd.text(line, 12, 10 + i * 16, c)
        self.draw_bottom(render)
