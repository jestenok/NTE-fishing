from typing import Final

import pydirectinput

pydirectinput.PAUSE = 0
pydirectinput.FAILSAFE = False

STATE_LEFT: Final[str] = "L"
STATE_RIGHT: Final[str] = "R"
STATE_IDLE: Final[str] = "."


class KeyHolder:
    """Управление двумя клавишами как удержанием. Не повторяет keyDown."""

    def __init__(self, key_left: str, key_right: str) -> None:
        self.key_left = key_left
        self.key_right = key_right
        self._left_down = False
        self._right_down = False

    def press_left(self) -> None:
        if self._right_down:
            pydirectinput.keyUp(self.key_right)
            self._right_down = False
        if not self._left_down:
            pydirectinput.keyDown(self.key_left)
            self._left_down = True

    def press_right(self) -> None:
        if self._left_down:
            pydirectinput.keyUp(self.key_left)
            self._left_down = False
        if not self._right_down:
            pydirectinput.keyDown(self.key_right)
            self._right_down = True

    def release_all(self) -> None:
        if self._left_down:
            pydirectinput.keyUp(self.key_left)
            self._left_down = False
        if self._right_down:
            pydirectinput.keyUp(self.key_right)
            self._right_down = False

    @property
    def state(self) -> str:
        if self._left_down:
            return STATE_LEFT
        if self._right_down:
            return STATE_RIGHT
        return STATE_IDLE
