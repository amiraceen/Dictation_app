"""
Native UI for Dictation: the floating recording pill and the main window.

Pill mirrors Wispr Flow's overlay window (observed in its main bundle):
transparent, frameless, "screen-saver" level, ignores mouse, visible on all
Spaces including full-screen apps.
"""

import json
import math
import os
import time

import objc
from AppKit import (
    NSBackingStoreBuffered, NSBezierPath, NSColor, NSMakeRect, NSPanel, NSScreen,
    NSScreenSaverWindowLevel, NSView, NSWindow, NSAnimationContext, NSApp,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless, NSWindowStyleMaskNonactivatingPanel,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSWindowStyleMaskFullSizeContentView, NSWindowTitleHidden,
    NSButton, NSTextField, NSFont, NSAppearance, NSStatusWindowLevel, NSMenu, NSMenuItem,
)
from Foundation import NSObject, NSTimer, NSURL
from PyObjCTools import AppHelper
from WebKit import WKWebView, WKWebViewConfiguration, WKUserContentController

# ─── Recording pill ──────────────────────────────────────────────────────────

PILL_W, PILL_H = 112, 34
BARS = 11
BOTTOM_GAP = 18          # px above the Dock / bottom of the visible frame


class WaveView(NSView):
    """Black capsule with white bars; bar heights follow the mic level."""

    def initWithFrame_(self, frame):
        self = objc.super(WaveView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.levels = [0.0] * BARS
        self.mode = "record"          # "record" | "busy" | "idle" (always-on bar)
        self.phase = 0.0
        return self

    def isFlipped(self):
        return True

    def drawRect_(self, rect):
        b = self.bounds()
        w, h = b.size.width, b.size.height
        idle = self.mode == "idle"
        NSColor.colorWithCalibratedWhite_alpha_(0.04, 0.6 if idle else 0.96).setFill()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(b, h / 2, h / 2).fill()
        NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.16).setStroke()
        rim = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(0.5, 0.5, w - 1, h - 1), h / 2 - 0.5, h / 2 - 0.5)
        rim.setLineWidth_(1.0)
        rim.stroke()

        bar_w, gap = 2.6, 3.4
        total = BARS * bar_w + (BARS - 1) * gap
        x0 = (w - total) / 2
        max_h, min_h = h - 14, 3.0
        NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.45 if idle else 1.0).setFill()
        for i in range(BARS):
            if idle:
                v = 0.0
            elif self.mode == "busy":
                # Travelling shimmer while transcribing.
                v = 0.25 + 0.25 * (1 + math.sin(self.phase * 6 - i * 0.7)) / 2
            else:
                v = self.levels[i]
            bh = min_h + (max_h - min_h) * v
            x = x0 + i * (bar_w + gap)
            y = (h - bh) / 2
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, y, bar_w, bh), bar_w / 2, bar_w / 2).fill()


class Pill(NSObject):
    """Owns the panel and a 60 fps timer. All methods run on the main thread."""

    def init(self):
        self = objc.super(Pill, self).init()
        if self is None:
            return None
        self.level = 0.0              # written by the audio thread
        self._smooth = [0.0] * BARS
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, PILL_W, PILL_H),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered, False)
        p = self.panel
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(True)
        p.setLevel_(NSScreenSaverWindowLevel)
        p.setIgnoresMouseEvents_(True)
        p.setHidesOnDeactivate_(False)
        p.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces
                                 | NSWindowCollectionBehaviorFullScreenAuxiliary
                                 | NSWindowCollectionBehaviorStationary)
        self.view = WaveView.alloc().initWithFrame_(NSMakeRect(0, 0, PILL_W, PILL_H))
        p.setContentView_(self.view)
        p.setAlphaValue_(0.0)
        self.timer = None
        self.always = False           # "Show the bar at all times"
        return self

    @objc.python_method
    def set_always(self, flag):
        self.always = bool(flag)
        if self.always and not self.panel.isVisible():
            self.show_("idle")
        elif not self.always and self.view.mode == "idle":
            self._fade_out()

    @objc.python_method
    def _place(self):
        scr = NSScreen.mainScreen() or NSScreen.screens()[0]
        vf = scr.visibleFrame()
        x = vf.origin.x + (vf.size.width - PILL_W) / 2
        self.panel.setFrameOrigin_((x, vf.origin.y + BOTTOM_GAP))

    def show_(self, mode):
        self.view.mode = mode
        if not self.panel.isVisible():
            self._place()
            self.panel.orderFrontRegardless()
        NSAnimationContext.beginGrouping()
        NSAnimationContext.currentContext().setDuration_(0.15)
        self.panel.animator().setAlphaValue_(1.0)
        NSAnimationContext.endGrouping()
        if mode == "idle":
            self._stop_timer()
            self.view.setNeedsDisplay_(True)
        elif self.timer is None:
            self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1 / 60, self, "tick:", None, True)

    def hide(self):
        self._smooth = [0.0] * BARS
        self.level = 0.0
        if self.always:
            self.show_("idle")
        else:
            self._fade_out()

    @objc.python_method
    def _fade_out(self):
        NSAnimationContext.beginGrouping()
        NSAnimationContext.currentContext().setDuration_(0.2)
        self.panel.animator().setAlphaValue_(0.0)
        NSAnimationContext.endGrouping()
        self._stop_timer()

    @objc.python_method
    def _stop_timer(self):
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None

    def tick_(self, _):
        v = self.view
        v.phase = time.monotonic()
        if v.mode == "record":
            # Speech RMS is ~0.01–0.1; map to 0–1 with a soft curve.
            lvl = min(1.0, (self.level * 14) ** 0.7)
            centre = (BARS - 1) / 2
            for i in range(BARS):
                shape = 1 - (abs(i - centre) / (centre + 1)) ** 1.6     # taller in the middle
                jitter = 0.75 + 0.25 * math.sin(v.phase * 13 + i * 1.9)
                target = lvl * shape * jitter
                k = 0.45 if target > self._smooth[i] else 0.18           # fast attack, slow release
                self._smooth[i] += (target - self._smooth[i]) * k
            v.levels = list(self._smooth)
        v.setNeedsDisplay_(True)


# ─── Toast (heads-up, call detected, warnings) ───────────────────────────────

TOAST_W = 340


class ToastView(NSView):
    def drawRect_(self, rect):
        b = self.bounds()
        NSColor.colorWithCalibratedWhite_alpha_(0.08, 0.97).setFill()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(b, 14, 14).fill()


class Toast(NSObject):
    """Small floating card at the top-right with up to two buttons. Main thread only.

    buttons: [(label, callback)]; the first is the primary action."""

    def initWithTitle_body_buttons_(self, title, body, buttons):
        self = objc.super(Toast, self).init()
        if self is None:
            return None
        self.callbacks = [cb for _, cb in buttons]
        self.on_close = None
        pad, btn_h = 16, 28
        title_f = self._label(title, NSFont.boldSystemFontOfSize_(13.5), 1.0)
        body_f = self._label(body, NSFont.systemFontOfSize_(12.5), 0.72) if body else None
        inner_w = TOAST_W - 2 * pad
        for f in (title_f, body_f):
            if f is not None:
                f.setFrameSize_((inner_w, f.cell().cellSizeForBounds_(NSMakeRect(0, 0, inner_w, 1000)).height))
        th = title_f.frame().size.height
        bh = body_f.frame().size.height if body_f else 0
        h = pad + th + (6 + bh if body_f else 0) + (12 + btn_h if buttons else 0) + pad

        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, TOAST_W, h),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered, False)
        p = self.panel
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(True)
        p.setLevel_(NSStatusWindowLevel)
        p.setHidesOnDeactivate_(False)
        p.setBecomesKeyOnlyIfNeeded_(True)
        p.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua"))
        p.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces
                                 | NSWindowCollectionBehaviorFullScreenAuxiliary)
        view = ToastView.alloc().initWithFrame_(NSMakeRect(0, 0, TOAST_W, h))
        p.setContentView_(view)

        y = h - pad - th
        title_f.setFrameOrigin_((pad, y))
        view.addSubview_(title_f)
        if body_f:
            y -= 6 + bh
            body_f.setFrameOrigin_((pad, y))
            view.addSubview_(body_f)
        x = TOAST_W - pad
        for i, (label, _) in reversed(list(enumerate(buttons))):
            b = NSButton.buttonWithTitle_target_action_(label, self, "clicked:")
            b.setTag_(i)
            b.sizeToFit()
            bw = max(b.frame().size.width + 8, 70)
            x -= bw
            b.setFrame_(NSMakeRect(x, pad - 2, bw, btn_h))
            if i == 0:
                b.setKeyEquivalent_("\r")        # primary button is highlighted
            view.addSubview_(b)
            x -= 8
        self.timer = None
        return self

    @objc.python_method
    def _label(self, text, font, alpha):
        f = NSTextField.wrappingLabelWithString_(text)
        f.setFont_(font)
        f.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(1.0, alpha))
        f.setSelectable_(False)
        return f

    def show_(self, timeout):
        scr = NSScreen.mainScreen() or NSScreen.screens()[0]
        vf = scr.visibleFrame()
        size = self.panel.frame().size
        self.panel.setFrameOrigin_((vf.origin.x + vf.size.width - size.width - 16,
                                    vf.origin.y + vf.size.height - size.height - 12))
        self.panel.setAlphaValue_(0.0)
        self.panel.orderFrontRegardless()
        NSAnimationContext.beginGrouping()
        NSAnimationContext.currentContext().setDuration_(0.18)
        self.panel.animator().setAlphaValue_(1.0)
        NSAnimationContext.endGrouping()
        if timeout:
            self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                timeout, self, "expire:", None, False)

    def clicked_(self, sender):
        cb = self.callbacks[sender.tag()] if sender.tag() < len(self.callbacks) else None
        self.close()
        if cb is not None:
            cb()

    def expire_(self, _):
        self.close()

    def close(self):
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None
        self.panel.orderOut_(None)
        if self.on_close is not None:
            self.on_close(self)


# ─── Web windows (main window and Notepad: WKWebView + JSON bridge) ─────────

def _plain(o):
    """NSDictionary/NSArray/NSNumber from WebKit → plain Python values."""
    if o is None or isinstance(o, bool):
        return o
    if isinstance(o, int):
        return int(o)
    if isinstance(o, float):
        return float(o)
    if isinstance(o, str):
        return str(o)
    if hasattr(o, "keys"):
        return {str(k): _plain(o[k]) for k in o.keys()}
    try:
        return [_plain(x) for x in o]
    except TypeError:
        return str(o)


class Bridge(NSObject):
    """Receives window.webkit.messageHandlers.app.postMessage({...}) calls.

    app.handle_message(msg, bridge) does the work; app.state_for(bridge) builds
    the JSON the page renders. mode is "main" or "notepad"."""

    def initWithApp_mode_(self, app, mode):
        self = objc.super(Bridge, self).init()
        if self is None:
            return None
        self.app = app
        self.mode = mode
        self.web = None
        self.note_id = None          # note shown in this window
        self.goto = None             # page to switch to on the next render
        return self

    def userContentController_didReceiveScriptMessage_(self, _ctrl, message):
        try:
            msg = _plain(message.body())
        except Exception:
            return
        if not isinstance(msg, dict):
            return
        if msg.get("type") == "copy":
            from AppKit import NSPasteboard, NSPasteboardTypeString
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(str(msg.get("text", "")), NSPasteboardTypeString)
            return                      # no re-render, so the "Copied ✓" state stays
        if self.app.handle_message(msg, self) is not False:
            self.push()

    def push(self):
        if self.web is not None:
            data = json.dumps(self.app.state_for(self))
            self.web.evaluateJavaScript_completionHandler_(
                f"window.render({data}, {json.dumps(self.mode)})", None)


class WebWindow(NSObject):

    SIZES = {"main": ((1000, 660), (760, 520), "Dictation"),
             "notepad": ((440, 680), (340, 420), "Notepad")}

    def initWithApp_html_mode_(self, app, html_path, mode):
        self = objc.super(WebWindow, self).init()
        if self is None:
            return None
        (w0, h0), min_size, title = self.SIZES[mode]
        self.bridge = Bridge.alloc().initWithApp_mode_(app, mode)
        cfg = WKWebViewConfiguration.alloc().init()
        ucc = WKUserContentController.alloc().init()
        ucc.addScriptMessageHandler_name_(self.bridge, "app")
        cfg.setUserContentController_(ucc)

        style = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable
                 | NSWindowStyleMaskResizable | NSWindowStyleMaskFullSizeContentView)
        self.win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, w0, h0), style, NSBackingStoreBuffered, False)
        w = self.win
        w.setTitle_(title)
        w.setTitlebarAppearsTransparent_(True)
        w.setTitleVisibility_(NSWindowTitleHidden)
        w.setMinSize_(min_size)
        w.setReleasedWhenClosed_(False)
        w.center()
        if mode == "notepad":
            w.setFrameAutosaveName_("DictationNotepad")

        self.web = WKWebView.alloc().initWithFrame_configuration_(w.contentView().bounds(), cfg)
        self.web.setAutoresizingMask_(18)                 # width + height sizable
        self.web.setValue_forKey_(False, "drawsBackground")
        w.setContentView_(self.web)
        self.bridge.web = self.web
        url = NSURL.fileURLWithPath_(html_path)
        self.web.loadFileURL_allowingReadAccessToURL_(url, url.URLByDeletingLastPathComponent())
        return self

    def show(self):
        NSApp.activateIgnoringOtherApps_(True)
        self.win.makeKeyAndOrderFront_(None)
        self.bridge.push()

    def refresh(self):
        if self.win.isVisible():
            self.bridge.push()


def install_edit_menu():
    """Menu-bar apps have no Edit menu, so ⌘C/⌘V/⌘X/⌘A/⌘Z do nothing in text fields
    (including pasting a dictation into a note). A hidden main menu fixes that."""
    main = NSMenu.alloc().init()
    app_item = NSMenuItem.alloc().init()
    main.addItem_(app_item)
    app_item.setSubmenu_(NSMenu.alloc().init())
    edit_item = NSMenuItem.alloc().init()
    main.addItem_(edit_item)
    edit = NSMenu.alloc().initWithTitle_("Edit")
    for title, action, key in [("Undo", "undo:", "z"), ("Redo", "redo:", "Z"), (None, None, None),
                               ("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"),
                               ("Select All", "selectAll:", "a")]:
        if title is None:
            edit.addItem_(NSMenuItem.separatorItem())
        else:
            edit.addItemWithTitle_action_keyEquivalent_(title, action, key)
    edit_item.setSubmenu_(edit)
    NSApp.setMainMenu_(main)


def on_main(fn, *args):
    """Run fn on the AppKit main thread (safe to call from any thread)."""
    AppHelper.callAfter(fn, *args)
