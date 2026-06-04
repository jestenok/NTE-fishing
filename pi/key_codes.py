from usb.device.keyboard import KeyCode


def _build_modifiers():
    mods = {
        "CTRL":  KeyCode.LEFT_CTRL,  "LCTRL":  KeyCode.LEFT_CTRL,
        "SHIFT": KeyCode.LEFT_SHIFT, "LSHIFT": KeyCode.LEFT_SHIFT,
        "ALT":   KeyCode.LEFT_ALT,   "LALT":   KeyCode.LEFT_ALT,
    }
    gui = getattr(KeyCode, "LEFT_GUI", None)
    if gui is not None:
        mods["WIN"] = gui
        mods["GUI"] = gui
        mods["LGUI"] = gui
    for name, attr in (("RCTRL", "RIGHT_CTRL"),
                       ("RSHIFT", "RIGHT_SHIFT"),
                       ("RALT", "RIGHT_ALT"),
                       ("RGUI", "RIGHT_GUI")):
        if hasattr(KeyCode, attr):
            mods[name] = getattr(KeyCode, attr)
    return mods


MODIFIERS = _build_modifiers()


class KeySpecParser:
    """`CTRL+SHIFT+A` -> [KeyCode...]"""

    def parse(self, spec):
        codes = []
        for part in spec.upper().split("+"):
            part = part.strip()
            if not part:
                continue
            if part in MODIFIERS:
                codes.append(MODIFIERS[part])
            elif hasattr(KeyCode, part):
                codes.append(getattr(KeyCode, part))
            elif part.isdigit() and len(part) == 1:
                codes.append(getattr(KeyCode, "N" + part))
            else:
                raise ValueError(part)
        return codes
