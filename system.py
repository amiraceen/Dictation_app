"""
Pure helpers for system features: the meeting keyboard shortcut, launch at
login, pausing media, and split-screen geometry. No AppKit imports, so it can
be tested anywhere; macos.py does the actual system calls.
"""

import os

# ─── Keyboard shortcut ───────────────────────────────────────────────────────

# Browser KeyboardEvent.code → macOS virtual key code (ANSI layout positions).
_LETTERS = dict(zip("asdfhgzxcvbqweryt", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17]))
_LETTERS.update({"o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40, "n": 45, "m": 46})
JS_CODE_TO_KEYCODE = {f"Key{c.upper()}": k for c, k in _LETTERS.items()}
JS_CODE_TO_KEYCODE.update({
    "Digit1": 18, "Digit2": 19, "Digit3": 20, "Digit4": 21, "Digit6": 22, "Digit5": 23,
    "Equal": 24, "Digit9": 25, "Digit7": 26, "Minus": 27, "Digit8": 28, "Digit0": 29,
    "BracketRight": 30, "BracketLeft": 33, "Quote": 39, "Semicolon": 41, "Backslash": 42,
    "Comma": 43, "Slash": 44, "Period": 47, "Backquote": 50, "Space": 49,
    "F1": 122, "F2": 120, "F3": 99, "F4": 118, "F5": 96, "F6": 97, "F7": 98, "F8": 100,
    "F9": 101, "F10": 109, "F11": 103, "F12": 111,
})

_KEY_LABELS = {"Space": "Space", "Minus": "-", "Equal": "=", "BracketLeft": "[", "BracketRight": "]",
               "Quote": "'", "Semicolon": ";", "Backslash": "\\", "Comma": ",", "Slash": "/",
               "Period": ".", "Backquote": "`"}

# CGEventFlags masks
FLAG_MASKS = {"shift": 0x20000, "ctrl": 0x40000, "alt": 0x80000, "cmd": 0x100000}
_MOD_ORDER = [("ctrl", "⌃"), ("alt", "⌥"), ("shift", "⇧"), ("cmd", "⌘")]


def shortcut_from_js(code, mods):
    """Build a shortcut from a browser key code and modifier names, or None if unusable.

    At least one of ⌃ ⌥ ⌘ is required so the shortcut can't fire while typing."""
    keycode = JS_CODE_TO_KEYCODE.get(code)
    mods = [m for m, _ in _MOD_ORDER if m in set(mods)]
    if keycode is None or not set(mods) & {"ctrl", "alt", "cmd"}:
        return None
    if code.startswith("Key"):
        key = code[3:]
    elif code.startswith("Digit"):
        key = code[5:]
    else:
        key = _KEY_LABELS.get(code, code)
    label = "".join(sym for m, sym in _MOD_ORDER if m in mods) + " " + key
    return {"keycode": keycode, "mods": mods, "label": label}


def shortcut_matches(shortcut, keycode, flags):
    """True if a key event (macOS keycode + CGEventFlags) is exactly this shortcut."""
    if keycode != shortcut["keycode"]:
        return False
    want = set(shortcut["mods"])
    return all(bool(flags & mask) == (name in want) for name, mask in FLAG_MASKS.items())


# ─── Launch at login ─────────────────────────────────────────────────────────

LOGIN_AGENT_LABEL = "com.amira.dictation.login"


def login_agent_path(home=None):
    home = home or os.path.expanduser("~")
    return os.path.join(home, "Library", "LaunchAgents", LOGIN_AGENT_LABEL + ".plist")


def app_bundle_path(executable):
    """'/Applications/Dictation.app/Contents/MacOS/Dictation' → '/Applications/Dictation.app'."""
    path = os.path.abspath(executable)
    while path and path != os.path.dirname(path):
        if path.endswith(".app"):
            return path
        path = os.path.dirname(path)
    return None


def login_program_args(frozen, executable, script):
    """How the login item starts the app: the bundle via `open`, or the source script."""
    bundle = app_bundle_path(executable) if frozen else None
    if bundle:
        return ["/usr/bin/open", "-a", bundle]
    return [executable, os.path.abspath(script)]


def login_agent_plist(program_args):
    return {"Label": LOGIN_AGENT_LABEL, "ProgramArguments": list(program_args),
            "RunAtLoad": True, "ProcessType": "Interactive"}


# ─── Media ───────────────────────────────────────────────────────────────────

# Apps we can ask to pause. `is running` checks never launch an app that's closed.
MEDIA_APPS = ["Music", "Spotify"]


def pause_media_script():
    """AppleScript that pauses playing players and returns their names, comma-separated."""
    lines = ["set paused to {}"]
    for app in MEDIA_APPS:
        lines += [f'if application "{app}" is running then',
                  f'  tell application "{app}"',
                  '    if player state is playing then',
                  '      pause',
                  f'      set end of paused to "{app}"',
                  '    end if',
                  '  end tell',
                  'end if']
    lines += ["set AppleScript's text item delimiters to \",\"",
              "return paused as text"]
    return "\n".join(lines)


def resume_media_script(apps):
    apps = [a for a in apps if a in MEDIA_APPS]
    return "\n".join(f'if application "{a}" is running then tell application "{a}" to play'
                     for a in apps)


def parse_paused(output):
    return [a for a in (s.strip() for s in output.split(",")) if a in MEDIA_APPS]


# ─── Split screen ────────────────────────────────────────────────────────────

def split_frames(visible, primary_height):
    """Left/right halves of a screen's visible frame, in Accessibility coordinates.

    visible is (x, y, w, h) in AppKit coordinates (origin bottom-left of the
    primary screen); Accessibility uses top-left. Returns ((x, y, w, h), (x, y, w, h))."""
    x, y, w, h = visible
    top = primary_height - (y + h)
    half = int(w // 2)
    return (int(x), int(top), half, int(h)), (int(x) + half, int(top), int(w) - half, int(h))
