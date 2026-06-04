class Command:
    def execute(self, args):
        raise NotImplementedError


class MoveCommand(Command):
    def __init__(self, pointer):
        self._pointer = pointer

    def execute(self, args):
        self._pointer.move(int(args[0]), int(args[1]))


class ClickCommand(Command):
    def __init__(self, clicker, button):
        self._clicker = clicker
        self._button = button

    def execute(self, args):
        self._clicker.click(self._button)


class ButtonStateCommand(Command):
    def __init__(self, clicker, down):
        self._clicker = clicker
        self._down = down

    def execute(self, args):
        button = args[0]
        if self._down:
            self._clicker.press(button)
        else:
            self._clicker.release(button)


class TapKeysCommand(Command):
    def __init__(self, typist, parser):
        self._typist = typist
        self._parser = parser

    def execute(self, args):
        self._typist.tap(self._parser.parse(args[0]))


class HoldKeysCommand(Command):
    def __init__(self, typist, parser):
        self._typist = typist
        self._parser = parser

    def execute(self, args):
        self._typist.hold(self._parser.parse(args[0]))


class ReleaseKeysCommand(Command):
    def __init__(self, typist, parser):
        self._typist = typist
        self._parser = parser

    def execute(self, args):
        self._typist.release_keys(self._parser.parse(args[0]))


class ReleaseAllKeysCommand(Command):
    def __init__(self, typist):
        self._typist = typist

    def execute(self, args):
        self._typist.release_all()
