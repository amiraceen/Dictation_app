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

# Option lists shown as drop-downs in the Settings page: (value, label).
NOTIFY_OPTIONS = [(-1, "Off"), (0, "At start"), (15, "15 sec"), (60, "1 min"),
                  (120, "2 min"), (300, "5 min")]
MAX_LENGTH_OPTIONS = [(30, "30 min"), (60, "1 hour"), (120, "2 hours"),
                      (180, "3 hours"), (240, "4 hours")]

# Default meeting shortcut: Option + M. keycode is the macOS virtual key code.
DEFAULT_SHORTCUT = {"keycode": 46, "mods": ["alt"], "label": "⌥ M"}

DEFAULTS = {
    # System → Dictation: a fixed language skips detection and roughly halves the wait
    "dictation_language": "auto",
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
    # Experimental
    "pause_media_while_dictating": False,
    # Notetaker → Meeting detection
    "notify_before_meeting": 15,          # seconds; -1 = off
    "show_next_meeting": True,
    "auto_detect_calls": True,
    "max_recording_minutes": 120,
    "stop_when_call_ends": True,
    "meeting_shortcut": DEFAULT_SHORTCUT,
    # Notetaker → While active
    "hide_from_screen_capture": False,
    # Notetaker → Notepad
    "open_notepad_on_start": True,
    "split_screen_on_join": False,
    # Notetaker → Transcript
    "show_live_transcript": True,
    "capture_system_audio": True,
}

_CHOICES = {
    "notify_before_meeting": {v for v, _ in NOTIFY_OPTIONS},
    "max_recording_minutes": {v for v, _ in MAX_LENGTH_OPTIONS},
    "dictation_language": {v for v, _ in LANGUAGE_OPTIONS},
    "speech_model": {v for v, _ in MODEL_OPTIONS},
    "ui_language": {v for v, _ in UI_LANGUAGE_OPTIONS},
}
_MODS = {"alt", "cmd", "ctrl", "shift"}


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
    if key == "meeting_shortcut" and isinstance(value, dict):
        out = dict(value)
        if isinstance(out.get("keycode"), float) and out["keycode"].is_integer():
            out["keycode"] = int(out["keycode"])
        return out
    return value


def _valid(key, value):
    """True if value is acceptable for key."""
    default = DEFAULTS[key]
    if key in _CHOICES:
        return type(value) is type(default) and value in _CHOICES[key]
    if key == "meeting_shortcut":
        return (isinstance(value, dict)
                and isinstance(value.get("keycode"), int) and 0 <= value["keycode"] < 128
                and isinstance(value.get("mods"), list) and value["mods"]
                and set(value["mods"]) <= _MODS
                and isinstance(value.get("label"), str))
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
    return {"notify_before_meeting": NOTIFY_OPTIONS, "max_recording_minutes": MAX_LENGTH_OPTIONS,
            "dictation_language": LANGUAGE_OPTIONS, "speech_model": MODEL_OPTIONS,
            "ui_language": UI_LANGUAGE_OPTIONS}
