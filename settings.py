"""
User settings for Dictation, stored as JSON in the app's data folder.

Pure Python (no AppKit) so it can be tested anywhere.
"""

import json
import os
import threading

from speed import LANGUAGE_OPTIONS
from models import MODEL_OPTIONS
from i18n import UI_LANGUAGE_OPTIONS
from system import DEFAULT_DICTATION_KEY, JS_CODE_TO_KEYCODE

DEFAULTS = {
    # System → Dictation: a fixed language skips detection and roughly halves the wait
    "dictation_language": "auto",
    # System → Transcribe: the key you hold to talk (a macOS key code; Right Option by default)
    "dictation_key": DEFAULT_DICTATION_KEY,
    # System → App settings: the language of Kalam's own screens and menus
    "ui_language": "en",
    # System → Transcribe: built-in "small", or the downloaded, more accurate "turbo"
    "speech_model": "small",
    # System → App settings
    "launch_at_login": False,
    "show_bar_always": False,
    "show_in_dock": False,
    # System → Sound
    "sounds": True,
    "mute_while_dictating": False,
    "pause_media_while_dictating": False,
}

_CHOICES = {
    "dictation_language": {v for v, _ in LANGUAGE_OPTIONS},
    "speech_model": {v for v, _ in MODEL_OPTIONS},
    "ui_language": {v for v, _ in UI_LANGUAGE_OPTIONS},
}


def _normalize(key, value):
    """Coerce bridge values (JS numbers arrive as floats or int subclasses) to plain types."""
    default = DEFAULTS[key]
    if isinstance(default, bool):
        return bool(value) if isinstance(value, bool) else value
    if isinstance(default, int) and not isinstance(value, bool):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, int):
            return int(value)
    return value


def _valid(key, value):
    """True if value is acceptable for key."""
    default = DEFAULTS[key]
    if key in _CHOICES:
        return type(value) is type(default) and value in _CHOICES[key]
    if key == "dictation_key":
        return type(value) is int and value in JS_CODE_TO_KEYCODE.values()
    return type(value) is type(default)


class Settings:
    """Thread-safe settings with defaults. Unknown or invalid values are ignored."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._values = dict(DEFAULTS)
        try:
            with open(path) as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                for k, v in saved.items():
                    if k in DEFAULTS and _valid(k, _normalize(k, v)):
                        self._values[k] = _normalize(k, v)
        except (OSError, ValueError):
            pass

    def __getitem__(self, key):
        with self._lock:
            return self._values[key]

    def all(self):
        with self._lock:
            return dict(self._values)

    def update(self, changes):
        """Apply valid changes, save, and return the keys that actually changed."""
        changed = []
        with self._lock:
            for k, v in dict(changes).items():
                if k in DEFAULTS:
                    v = _normalize(k, v)
                if k in DEFAULTS and _valid(k, v) and self._values[k] != v:
                    self._values[k] = v
                    changed.append(k)
            if changed:
                tmp = self.path + ".tmp"
                with open(tmp, "w") as f:
                    json.dump(self._values, f, indent=2, ensure_ascii=False)
                os.replace(tmp, self.path)
        return changed


def options():
    """Drop-down choices for the Settings page."""
    return {"dictation_language": LANGUAGE_OPTIONS, "speech_model": MODEL_OPTIONS,
            "ui_language": UI_LANGUAGE_OPTIONS}
