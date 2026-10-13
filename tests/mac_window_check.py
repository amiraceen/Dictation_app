"""Opens Kalam's real window (WKWebView, the engine the app uses on a Mac) with a
stand-in app, clicks buttons with real mouse events and checks what the app receives.

    python tests/mac_window_check.py        # macOS only; the build workflow runs it

Prints one line per check and exits non-zero if any fail.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from AppKit import (NSApplication, NSApplicationActivationPolicyRegular, NSEvent,  # noqa: E402
                    NSEventTypeLeftMouseDown, NSEventTypeLeftMouseUp, NSPasteboard, NSPasteboardTypeString)
from Foundation import NSDate, NSProcessInfo, NSRunLoop  # noqa: E402

import ui  # noqa: E402

NOW = time.time()
NOTE = {"id": "a1", "title": "Weekly sync", "body": "Decisions", "created": NOW - 900, "updated": NOW,
        "meeting": True, "duration": 754, "recording": False,
        "transcript": [{"t": 0, "text": "Okay, let us start."}]}
STATE = {
    "glass": True,
    "history": [{"ts": NOW - 60, "text": "Hello from the history", "words": 4, "secs": 2}],
    "dictionary": ["Kalam"], "snippets": {"my email": "a@b.c"}, "stats": {"words": 4, "wpm": 120, "streak": 1},
    "settings": {"dictation_language": "auto", "speech_model": "small", "launch_at_login": False,
                 "show_bar_always": False, "show_in_dock": False, "sounds": True, "mute_while_dictating": False,
                 "pause_media_while_dictating": False, "notify_before_meeting": 15, "show_next_meeting": True,
                 "auto_detect_calls": True, "max_recording_minutes": 120, "stop_when_call_ends": True,
                 "meeting_shortcut": {"label": "⌥ M"}, "hide_from_screen_capture": False,
                 "open_notepad_on_start": True, "split_screen_on_join": False, "show_live_transcript": True,
                 "capture_system_audio": True, "ui_language": "en"},
    "options": {"dictation_language": [["auto", "Arabic or English (auto)"], ["ar", "Arabic"], ["en", "English"]],
                "speech_model": [["small", "Fast"], ["turbo", "Accurate"]],
                "notify_before_meeting": [[15, "15 sec"]], "max_recording_minutes": [[120, "2 hours"]]},
    "notes": [{"id": "a1", "title": "Weekly sync", "created": NOW - 900, "meeting": True, "duration": 754,
               "recording": False, "preview": "Decisions"},
              {"id": "b2", "title": "Groceries", "created": NOW - 86400, "meeting": False, "duration": 0,
               "recording": False, "preview": "Milk"}],
    "note": NOTE, "notetaker": {"active": False}, "calendar": "granted", "goto": None,
    "model": {"choice": "small", "active": "Whisper small", "ready": True},
    "voicetest": {"phrases": [], "results": None, "recording": None, "rec_started": None, "running": None,
                  "model": "Whisper small", "language": "auto"},
}


class FakeApp:
    def __init__(self):
        self.received = []

    def state_for(self, bridge):
        return STATE

    def handle_message(self, msg, bridge):
        self.received.append(msg)
        return msg.get("type") in ("ready", "openNote")


def spin(secs):
    end = time.time() + secs
    while time.time() < end:
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.02))


def js(web, code, timeout=5):
    box = {}

    def done(result, error):
        box["r"], box["e"] = result, error

    web.evaluateJavaScript_completionHandler_(code, done)
    end = time.time() + timeout
    while "r" not in box and time.time() < end:
        spin(0.02)
    return box.get("r")


fails = 0


def check(name, ok, detail=""):
    global fails
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok or not detail else '  → ' + str(detail)}", flush=True)


def click(win, web, selector, times=1):
    """Real mouse-down/up events at the middle of the element, sent through the window."""
    win = getattr(win, "win", win)          # ui.WebWindow wraps the NSWindow
    rect = js(web, f"(() => {{ const e = document.querySelector({selector!r}); if (!e) return null;"
                   f" e.scrollIntoView({{block: 'center'}}); const r = e.getBoundingClientRect();"
                   f" return [r.left + r.width / 2, r.top + r.height / 2]; }})()")
    if not rect:
        return False
    x, y = float(rect[0]), float(rect[1])
    p = (x, y) if web.isFlipped() else (x, web.bounds().size.height - y)
    loc = web.convertPoint_toView_(p, None)
    for _ in range(times):
        for kind in (NSEventTypeLeftMouseDown, NSEventTypeLeftMouseUp):
            ev = NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
                kind, loc, 0, NSProcessInfo.processInfo().systemUptime(),
                win.windowNumber(), None, 0, 1, 1.0)
            win.sendEvent_(ev)
            spin(0.05)
        spin(0.35)
    return True


def last(app):
    msgs = [m for m in app.received if m.get("type") not in ("ready", "dragRegion")]
    return msgs[-1] if msgs else {}


def main():
    nsapp = NSApplication.sharedApplication()
    nsapp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    app = FakeApp()
    win = ui.WebWindow.alloc().initWithApp_html_mode_(app, os.path.join(ROOT, "web", "index.html"), "main")
    win.show()
    nsapp.activateIgnoringOtherApps_(True)
    web = win.web
    end = time.time() + 15
    while time.time() < end and js(web, "typeof window.render === 'function' && !!document.querySelector('#nitems .nitem')") is not True:
        spin(0.2)
    spin(0.5)
    check("window loaded and rendered", js(web, "!!document.querySelector('#nitems .nitem')") is True)
    check("page told the app where the top bar is", getattr(web, "drag_band", 0) > 40 and len(web.no_drag) >= 6,
          (getattr(web, "drag_band", None), getattr(web, "no_drag", None)))
    if hasattr(web, "drag_here"):
        nb = web.no_drag[0] if web.no_drag else (0, 0, 0, 0)
        check("empty top bar drags the window", web.drag_here(500 if web.bounds().size.width > 900 else 300, 20)
              or web.drag_here(140, 60))
        check("top bar buttons don't drag", not web.drag_here(nb[0] + nb[2] / 2, nb[1] + nb[3] / 2))
        check("page content doesn't drag", not web.drag_here(400, 300))

    js(web, "window.__errors = []; window.addEventListener('error', e => window.__errors.push(e.message));")

    # Circle navigation
    check("click Notes circle", click(win, web, '.nb[data-p="notes"]'))
    check("Notes page opens", js(web, "document.getElementById('notes').classList.contains('on')") is True)

    # Notes buttons, the ones reported broken
    for act, kind in (("copy", "copyNote"), ("export", "exportNote"), ("pad", "openNotepad")):
        app.received.clear()
        click(win, web, f'#editor [data-act="{act}"]')
        m = last(app)
        check(f"note {act} button sends {kind}", m.get("type") == kind and m.get("id") == "a1", m or app.received)
    app.received.clear()
    click(win, web, '#editor [data-act="delete"]')
    check("Delete: first click asks", not [m for m in app.received if m.get("type") == "deleteNote"]
          and "Click again" in (js(web, "document.querySelector('#editor [data-act=delete]').textContent") or ""),
          app.received)
    click(win, web, '#editor [data-act="delete"]')
    m = last(app)
    check("Delete: second click deletes", m.get("type") == "deleteNote" and m.get("id") == "a1", m or app.received)
    app.received.clear()
    click(win, web, "#newNote")
    check("New note button", last(app).get("type") == "newNote", app.received)
    click(win, web, "#ntToggle")
    check("Notetaker button", last(app).get("type") == "startNotetaker", app.received)
    click(win, web, '.nitem[data-note="b2"]')
    m = last(app)
    check("clicking a note opens it", m.get("type") == "openNote" and m.get("id") == "b2", m)

    # Transcribe page: Copy (handled by the window itself) and Clear
    click(win, web, '.nb[data-p="home"]')
    NSPasteboard.generalPasteboard().clearContents()
    js(web, "document.querySelector('#history [data-copy=\"0\"]').style.opacity = 1")
    click(win, web, '#history [data-copy="0"]')
    got = NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString)
    check("history Copy puts the text on the clipboard", got == "Hello from the history", got)
    app.received.clear()
    click(win, web, "#clear", times=2)
    check("Clear history (two clicks)", last(app).get("type") == "clearHistory", app.received)

    # Settings: a toggle and a menu
    click(win, web, '.nb[data-p="settings"]')
    app.received.clear()
    click(win, web, 'label.tog:has([data-set="sounds"])')
    m = last(app)
    check("Settings toggle", m.get("type") == "saveSettings" and m.get("changes") == {"sounds": False}, m)

    errs = js(web, "window.__errors") or []
    check("no script errors", not errs, errs)
    print("\n" + (f"{fails} check(s) failed" if fails else "All checks passed"), flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
