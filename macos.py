"""
macOS system calls for System settings. Every function here fails soft: a missing
permission or an older macOS turns a feature off instead of crashing the app.
"""

import os
import plistlib
import subprocess
import threading

import system

# ─── Launch at login and Dock ─────────────────────────────────────────────────

def set_launch_at_login(enabled, frozen, executable, script):
    path = system.login_agent_path()
    try:
        if enabled:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                plistlib.dump(system.login_agent_plist(
                    system.login_program_args(frozen, executable, script)), f)
        elif os.path.exists(path):
            os.remove(path)
        return True
    except OSError as e:
        print(f"Launch at login: {e}", flush=True)
        return False


def launch_at_login_enabled():
    return os.path.exists(system.login_agent_path())


def set_dock_icon(show):
    from AppKit import NSApp, NSApplication
    app = NSApp or NSApplication.sharedApplication()
    app.setActivationPolicy_(0 if show else 1)     # Regular / Accessory



# ─── Sound, mute and media ───────────────────────────────────────────────────

def play_sound(name):
    try:
        from AppKit import NSSound
        s = NSSound.soundNamed_(name)
        if s is not None:
            s.setVolume_(0.35)
            s.play()
    except Exception:
        pass


_playing = []


def play_file(path):
    """Play an audio file (voice test playback). Keeps a reference so it isn't freed mid-play."""
    try:
        from AppKit import NSSound
        sound = NSSound.alloc().initWithContentsOfFile_byReference_(path, True)
        if sound is not None:
            _playing[:] = [s for s in _playing if s.isPlaying()] + [sound]
            sound.play()
    except Exception as e:
        print(f"Playback failed: {e}", flush=True)


def _osascript(script):
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


class AudioDucker:
    """Mutes output and/or pauses media while dictating, then puts things back.
    osascript is slow (~100 ms), so the work runs on one background thread, in
    order: a quick press can't unmute before the mute has happened."""

    def __init__(self):
        import queue
        self._jobs = queue.Queue()
        self._muted_by_us = False
        self._paused = []
        threading.Thread(target=self._run, daemon=True).start()

    def begin(self, mute, pause):
        if mute or pause:
            self._jobs.put((self._begin, (mute, pause)))

    def end(self):
        self._jobs.put((self._end, ()))

    def _run(self):
        while True:
            fn, args = self._jobs.get()
            try:
                fn(*args)
            except Exception as e:
                print(f"Audio ducking: {e}", flush=True)

    def _begin(self, mute, pause):
        if pause:
            self._paused = system.parse_paused(_osascript(system.pause_media_script()))
        if mute and _osascript("output muted of (get volume settings)") == "false":
            _osascript("set volume with output muted")
            self._muted_by_us = True

    def _end(self):
        if self._muted_by_us:
            _osascript("set volume without output muted")
            self._muted_by_us = False
        if self._paused:
            _osascript(system.resume_media_script(self._paused))
            self._paused = []
