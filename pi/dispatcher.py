class DispatchListener:
    def on_command(self, name, args):
        pass

    def on_unknown(self, name):
        pass

    def on_error(self, name, exc):
        pass


class CommandDispatcher:
    def __init__(self):
        self._commands = {}
        self._listeners = []

    def register(self, name, command):
        self._commands[name.upper()] = command

    def add_listener(self, listener):
        self._listeners.append(listener)

    def dispatch(self, line):
        parts = line.split()
        if not parts:
            return
        name = parts[0].upper()
        args = parts[1:]
        cmd = self._commands.get(name)
        if cmd is None:
            self._notify("on_unknown", name)
            return
        try:
            cmd.execute(args)
        except Exception as e:
            self._notify("on_error", name, e)
            return
        self._notify("on_command", name, args)

    def _notify(self, method_name, *args):
        for listener in self._listeners:
            try:
                getattr(listener, method_name)(*args)
            except Exception:
                pass
