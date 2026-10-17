"""
Pure helpers for system features: the dictation key, launch at login and pausing media.
No AppKit imports, so it can be tested anywhere; macos.py does the actual
system calls.
"""

import os

# ─── Dictation key ───────────────────────────────────────────────────────────

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
    "F9": 101, "F10": 109, "F11": 103, "F12": 111, "F13": 105, "F14": 107, "F15": 113,
    "AltRight": 61, "AltLeft": 58, "MetaRight": 54, "MetaLeft": 55, "ControlRight": 62,
    "ControlLeft": 59, "ShiftRight": 60, "ShiftLeft": 56, "Fn": 63,
})

# Modifier keys arrive as "flags changed" events; this device bit says whether that exact key is down.
MODIFIER_DOWN_MASK = {58: 0x20, 61: 0x40, 55: 0x08, 54: 0x10, 59: 0x01, 62: 0x2000,
                      56: 0x02, 60: 0x04, 63: 0x800000}

DEFAULT_DICTATION_KEY = 61                    # Right Option
# Offered in Settings; any other key can be recorded with "Other key…".
DICTATION_KEY_PRESETS = [61, 58, 54, 62, 60, 63, 96, 97]

_SIDE = {"en": ("Right", "Left"), "ar": ("اليمين", "اليسار")}
_MODS = {61: ("⌥", 0), 58: ("⌥", 1), 54: ("⌘", 0), 55: ("⌘", 1), 62: ("⌃", 0), 59: ("⌃", 1),
         60: ("⇧", 0), 56: ("⇧", 1)}
_SYMBOLS = {"Space": "Space", "Minus": "-", "Equal": "=", "BracketLeft": "[", "BracketRight": "]",
            "Quote": "'", "Semicolon": ";", "Backslash": "\\", "Comma": ",", "Slash": "/",
            "Period": ".", "Backquote": "`"}
_CODE_FOR = {v: k for k, v in JS_CODE_TO_KEYCODE.items()}


def is_modifier(keycode):
    return keycode in MODIFIER_DOWN_MASK


def key_label(keycode, lang="en"):
    """How a key is written in the app: "Right ⌥" / "⌥ اليمين", "Fn", "F5", "M"."""
    if keycode in _MODS:
        sym, side = _MODS[keycode]
        word = _SIDE["ar" if lang == "ar" else "en"][side]
        return f"{sym} {word}" if lang == "ar" else f"{word} {sym}"
    if keycode == 63:
        return "Fn 🌐"
    code = _CODE_FOR.get(keycode)
    if code is None:
        return f"#{keycode}"
    if code.startswith("Key"):
        return code[3:]
    if code.startswith("Digit"):
        return code[5:]
    return _SYMBOLS.get(code, code)


def keycode_from_js(code):
    """macOS key code for a browser KeyboardEvent.code, or None if Kalam can't use that key."""
    return JS_CODE_TO_KEYCODE.get(str(code))


# ─── Launch at login ─────────────────────────────────────────────────────────

LOGIN_AGENT_LABEL = "com.amira.kalam.login"


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

