"""
macOS system calls for the Notetaker and System settings. Every function here
fails soft: a missing permission or an older macOS turns a feature off instead
of crashing the app. The decisions live in meetings.py / system.py.
"""

import ctypes
import os
import plistlib
import subprocess
import threading

import numpy as np

import system

# ─── Mic in use by another app (call detection) ──────────────────────────────

_ca = None


class _Addr(ctypes.Structure):
    _fields_ = [("mSelector", ctypes.c_uint32), ("mScope", ctypes.c_uint32),
                ("mElement", ctypes.c_uint32)]


def _fourcc(s):
    return int.from_bytes(s.encode("ascii"), "big")


def _coreaudio():
    global _ca
    if _ca is None:
        _ca = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreAudio.framework/CoreAudio")
        _ca.AudioObjectGetPropertyDataSize.argtypes = [
            ctypes.c_uint32, ctypes.POINTER(_Addr), ctypes.c_uint32, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32)]
        _ca.AudioObjectGetPropertyData.argtypes = [
            ctypes.c_uint32, ctypes.POINTER(_Addr), ctypes.c_uint32, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
    return _ca


_SYSTEM_OBJECT = 1
_GLOBAL = "glob"


def _get_value(obj, selector, ctype):
    ca = _coreaudio()
    addr = _Addr(_fourcc(selector), _fourcc(_GLOBAL), 0)
    val = ctype()
    size = ctypes.c_uint32(ctypes.sizeof(val))
    if ca.AudioObjectGetPropertyData(obj, ctypes.byref(addr), 0, None, ctypes.byref(size),
                                     ctypes.byref(val)) != 0:
        return None
    return val.value


def _get_ids(obj, selector):
    ca = _coreaudio()
    addr = _Addr(_fourcc(selector), _fourcc(_GLOBAL), 0)
    size = ctypes.c_uint32(0)
    if ca.AudioObjectGetPropertyDataSize(obj, ctypes.byref(addr), 0, None, ctypes.byref(size)) != 0:
        return None
    n = size.value // 4
    arr = (ctypes.c_uint32 * max(n, 1))()
    if ca.AudioObjectGetPropertyData(obj, ctypes.byref(addr), 0, None, ctypes.byref(size), arr) != 0:
        return None
    return list(arr[:size.value // 4])


# Processes that use the mic but aren't calls.
_NOT_CALLS = {"corespeechd", "siri", "assistantd", "speechrecognitioncore", "localspeechrecognition",
              "heard", "wispr flow", "dictation", "kalam", "superwhisper", "voiceover", "replayd",
              "screencaptureui", "screencapture", "controlcenter", "universalaccessd", "coreaudiod"}
_RENAME = {"avconferenced": "FaceTime"}
_SYSTEM_CALLERS = {"avconferenced"}       # FaceTime's call service lives outside any app


def _process_path(pid):
    try:
        libc = ctypes.CDLL("/usr/lib/libproc.dylib")
        buf = ctypes.create_string_buffer(4096)
        if libc.proc_pidpath(pid, buf, 4096) > 0:
            return buf.value.decode("utf-8", "replace")
    except Exception:
        pass
    return None


def call_app(name, path):
    """The app name to show for a process recording from the mic, or None if it isn't a
    call app. Only apps the user opens count (Zoom, Teams, browsers, FaceTime...): macOS
    background services such as replayd (screen recording) live outside any .app bundle
    or in /System/Library and are ignored."""
    raw = (name or "").lower()
    if raw in _SYSTEM_CALLERS:
        return _RENAME.get(raw, name)
    if path:
        if ".app/" not in path or path.startswith("/System/Library/"):
            return None
        # Helpers live inside the main app: '/Applications/Google Chrome.app/.../Google Chrome Helper.app/...'
        name = path.split(".app/")[0].rsplit("/", 1)[-1]
    name = _app_name(name)
    if not name or name.lower() in _NOT_CALLS or name.lower().startswith(("dictation", "kalam")):
        return None
    return name


def _process_name(pid):
    try:
        from AppKit import NSRunningApplication
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app is not None and app.localizedName():
            return str(app.localizedName())
    except Exception:
        pass
    try:
        libc = ctypes.CDLL("/usr/lib/libproc.dylib")
        buf = ctypes.create_string_buffer(256)
        if libc.proc_name(pid, buf, 256) > 0:
            return buf.value.decode("utf-8", "replace")
    except Exception:
        pass
    return None


def _app_name(name):
    """'Google Chrome Helper (Renderer)' → 'Google Chrome'."""
    if not name:
        return None
    name = _RENAME.get(name, name)
    for marker in (" Helper", " Web Content", " Networking"):
        if marker in name:
            name = name.split(marker)[0]
    return name


def mic_used_by_other_app(self_using_mic):
    """(True, app name) if another app is recording from a mic, (False, None) if not,
    None if unknown (old macOS while we're recording ourselves)."""
    try:
        procs = _get_ids(_SYSTEM_OBJECT, "prs#")        # kAudioHardwarePropertyProcessObjectList, macOS 14+
        if procs is not None:
            me = os.getpid()
            for p in procs:
                if not _get_value(p, "piri", ctypes.c_uint32):     # kAudioProcessPropertyIsRunningInput
                    continue
                pid = _get_value(p, "ppid", ctypes.c_int32)        # kAudioProcessPropertyPID
                if not pid or pid == me:
                    continue
                name = call_app(_process_name(pid), _process_path(pid))
                if name is None:
                    continue
                return True, name
            return False, None
        # macOS 13: we can only ask whether the default input device is busy.
        if self_using_mic:
            return None
        dev = _get_value(_SYSTEM_OBJECT, "dIn ", ctypes.c_uint32)  # kAudioHardwarePropertyDefaultInputDevice
        if not dev:
            return False, None
        busy = _get_value(dev, "gone", ctypes.c_uint32)            # kAudioDevicePropertyDeviceIsRunningSomewhere
        return (bool(busy), None) if busy is not None else None
    except Exception:
        return None


# ─── Calendar (EventKit) ─────────────────────────────────────────────────────

class Calendar:
    """Upcoming events from the macOS Calendar (covers iCloud, Google and Exchange
    accounts added in System Settings → Internet Accounts)."""

    def __init__(self):
        self._store = None
        self._requested = False
        self.status = "unknown"           # unknown | granted | denied | unavailable

    def _ensure(self):
        if self._store is not None:
            return self.status == "granted"
        try:
            import EventKit
        except ImportError:
            self.status = "unavailable"
            self._store = False
            return False
        self._ek = EventKit
        self._store = EventKit.EKEventStore.alloc().init()
        st = EventKit.EKEventStore.authorizationStatusForEntityType_(EventKit.EKEntityTypeEvent)
        if st == 3:                                   # authorized / full access
            self.status = "granted"
        elif st in (1, 2, 4):                         # restricted / denied / write-only
            self.status = "denied"
        elif not self._requested:
            self._requested = True

            def done(granted, _err=None):
                self.status = "granted" if granted else "denied"
            if hasattr(self._store, "requestFullAccessToEventsWithCompletion_"):
                self._store.requestFullAccessToEventsWithCompletion_(done)       # macOS 14+
            else:
                self._store.requestAccessToEntityType_completion_(EventKit.EKEntityTypeEvent, done)
        return self.status == "granted"

    def events(self, now, horizon=86400):
        if not self._ensure():
            return []
        try:
            from Foundation import NSDate
            start = NSDate.dateWithTimeIntervalSince1970_(now - 3600)
            end = NSDate.dateWithTimeIntervalSince1970_(now + horizon)
            pred = self._store.predicateForEventsWithStartDate_endDate_calendars_(start, end, None)
            out = []
            for e in self._store.eventsMatchingPredicate_(pred) or []:
                if e.status() == 3:                   # EKEventStatusCanceled
                    continue
                out.append({"id": str(e.calendarItemIdentifier()), "title": str(e.title() or "Meeting"),
                            "start": e.startDate().timeIntervalSince1970(),
                            "end": e.endDate().timeIntervalSince1970(), "all_day": bool(e.isAllDay())})
            return out
        except Exception as ex:
            print(f"Calendar error: {ex}", flush=True)
            return []


# ─── System audio (other meeting participants) via ScreenCaptureKit ──────────

_OutputClass = None


def _output_class():
    """Defined lazily: ScreenCaptureKit is only imported when the Notetaker starts."""
    global _OutputClass
    if _OutputClass is None:
        import objc
        import ScreenCaptureKit  # noqa: F401  (registers the SCStreamOutput protocol)
        from Foundation import NSObject

        class SystemAudioOutput(NSObject, protocols=[objc.protocolNamed("SCStreamOutput")]):
            def initWithCallback_(self, cb):
                self = objc.super(SystemAudioOutput, self).init()
                if self is None:
                    return None
                self.cb = cb
                from notetaker import SystemAudioConverter
                self.converter = SystemAudioConverter()
                return self

            def stream_didOutputSampleBuffer_ofType_(self, _stream, sbuf, kind):
                if kind != 1:                        # SCStreamOutputTypeAudio (screen frames are ignored)
                    return
                try:
                    import CoreMedia
                    block = CoreMedia.CMSampleBufferGetDataBuffer(sbuf)
                    if block is None:
                        return
                    n = CoreMedia.CMBlockBufferGetDataLength(block)
                    frames = CoreMedia.CMSampleBufferGetNumSamples(sbuf)
                    status, data = CoreMedia.CMBlockBufferCopyDataBytes(block, 0, n, None)
                    if status == 0 and data:
                        mono = self.converter.convert(np.frombuffer(bytes(data), dtype=np.float32), frames)
                        if len(mono):
                            self.cb(mono)
                except Exception as e:
                    if not getattr(self, "logged", False):
                        self.logged = True
                        print(f"System audio buffer error: {e}", flush=True)

        _OutputClass = SystemAudioOutput
    return _OutputClass


SYSTEM_AUDIO_FAILED = ("Only your microphone is being transcribed: macOS didn't start recording the call's sound. "
                       "Try quitting and reopening Kalam, and check it's allowed in System Settings → "
                       "Privacy & Security → Screen & System Audio Recording.")


def _capture_queue():
    """A serial queue for audio buffers (keeps them off the main thread)."""
    try:
        import dispatch
        return dispatch.dispatch_queue_create(b"kalam.system-audio", None)
    except Exception:
        return None


class SystemAudioCapture:
    """Captures what the Mac plays (the other people on the call), delivered as 16 kHz mono float32.
    The stream uses ScreenCaptureKit's default 48 kHz stereo (asking it for 16 kHz mono
    failed on some Macs with error -3818); SystemAudioConverter does the conversion.
    Needs Screen & System Audio Recording permission; macOS asks on first use."""

    def __init__(self, on_samples, on_error):
        self.on_samples, self.on_error = on_samples, on_error
        self._stream = None
        self._stopped = False

    def start(self):
        import ScreenCaptureKit as SCK
        import CoreMedia
        out_cls = _output_class()

        def got_content(content, error):
            if self._stopped:
                return
            if error is not None or content is None or not content.displays():
                self.on_error("Other participants aren't being recorded: allow Kalam in System Settings → "
                              "Privacy & Security → Screen & System Audio Recording.")
                return
            try:
                flt = SCK.SCContentFilter.alloc().initWithDisplay_excludingWindows_(content.displays()[0], [])
                cfg = SCK.SCStreamConfiguration.alloc().init()
                cfg.setCapturesAudio_(True)
                cfg.setExcludesCurrentProcessAudio_(True)
                cfg.setSampleRate_(48000)
                cfg.setChannelCount_(2)
                cfg.setWidth_(128)                    # we only want audio: keep video small and slow
                cfg.setHeight_(128)
                cfg.setMinimumFrameInterval_(CoreMedia.CMTimeMake(1, 1))
                self._output = out_cls.alloc().initWithCallback_(self.on_samples)
                stream = SCK.SCStream.alloc().initWithFilter_configuration_delegate_(flt, cfg, None)
                queue = _capture_queue()
                for kind in (0, 1):                   # screen output too, so frames aren't reported as dropped
                    ok, err = stream.addStreamOutput_type_sampleHandlerQueue_error_(self._output, kind, queue, None)
                    if not ok:
                        raise RuntimeError(str(err))

                def started(err):
                    if err is not None:
                        print(f"System audio capture failed: {err}", flush=True)
                        self.on_error(SYSTEM_AUDIO_FAILED)
                stream.startCaptureWithCompletionHandler_(started)
                self._stream = stream
            except Exception as e:
                print(f"System audio capture failed: {e}", flush=True)
                self.on_error(SYSTEM_AUDIO_FAILED)

        SCK.SCShareableContent.getShareableContentWithCompletionHandler_(got_content)

    def stop(self):
        self._stopped = True
        if self._stream is not None:
            self._stream.stopCaptureWithCompletionHandler_(None)
            self._stream = None


# ─── Split screen (Accessibility) ────────────────────────────────────────────

def _ax_set_frame(win, frame):
    import ApplicationServices as AS
    import Quartz
    x, y, w, h = frame
    point_t = getattr(AS, "kAXValueCGPointType", getattr(AS, "kAXValueTypeCGPoint", 1))
    size_t = getattr(AS, "kAXValueCGSizeType", getattr(AS, "kAXValueTypeCGSize", 2))
    AS.AXUIElementSetAttributeValue(win, AS.kAXPositionAttribute, AS.AXValueCreate(point_t, Quartz.CGPoint(x, y)))
    AS.AXUIElementSetAttributeValue(win, AS.kAXSizeAttribute, AS.AXValueCreate(size_t, Quartz.CGSize(w, h)))


def find_meeting_app(name_hint):
    """The running app to put on the left: the one using the mic, else the frontmost other app."""
    from AppKit import NSWorkspace
    me = os.getpid()
    apps = [a for a in NSWorkspace.sharedWorkspace().runningApplications()
            if a.activationPolicy() == 0 and a.processIdentifier() != me]
    if name_hint:
        for a in apps:
            if str(a.localizedName() or "") == name_hint:
                return a
    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    if front is not None and front.processIdentifier() != me:
        return front
    return None


def split_screen(app, ns_window):
    """Meeting app's window on the left half, our notepad on the right half."""
    try:
        import ApplicationServices as AS
        from AppKit import NSScreen
        screen = ns_window.screen() or NSScreen.mainScreen()
        vf = screen.visibleFrame()
        primary_h = NSScreen.screens()[0].frame().size.height
        left, _ = system.split_frames((vf.origin.x, vf.origin.y, vf.size.width, vf.size.height), primary_h)
        if app is not None:
            ax_app = AS.AXUIElementCreateApplication(app.processIdentifier())
            err, win = AS.AXUIElementCopyAttributeValue(ax_app, AS.kAXFocusedWindowAttribute, None)
            if err != 0 or win is None:
                err, wins = AS.AXUIElementCopyAttributeValue(ax_app, AS.kAXWindowsAttribute, None)
                win = wins[0] if err == 0 and wins else None
            if win is not None:
                _ax_set_frame(win, left)
        half = int(vf.size.width // 2)
        ns_window.setFrame_display_animate_(
            ((vf.origin.x + half, vf.origin.y), (vf.size.width - half, vf.size.height)), True, True)
        return True
    except Exception as e:
        print(f"Split screen failed: {e}", flush=True)
        return False


# ─── Launch at login, Dock, window capture ───────────────────────────────────

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


def set_hidden_from_capture(window, hidden):
    """NSWindowSharingNone keeps a window out of screenshots and screen sharing."""
    try:
        window.setSharingType_(0 if hidden else 1)
    except Exception:
        pass


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
