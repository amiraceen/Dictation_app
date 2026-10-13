"""
Kalam's menus and alerts in English or Arabic. The wording lives in web/strings.js, the
same file the window uses, so each phrase is written once. No AppKit here.
"""

import json
import os

UI_LANGUAGE_OPTIONS = [("en", "English"), ("ar", "العربية")]
_strings = {}


def load(path):
    """Read web/strings.js ('window.STRINGS = {...};')."""
    global _strings
    with open(path, encoding="utf-8") as f:
        src = f.read()
    _strings = json.loads(src[src.index("{"):src.rindex("}") + 1])
    return _strings


def tr(name, lang="en", **values):
    """The phrase called name in lang (falls back to English, then to the name itself)."""
    entry = _strings.get(name)
    text = (entry.get(lang) or entry.get("en")) if entry else name
    for k, v in values.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def default_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "strings.js")
