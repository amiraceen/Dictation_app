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
        self.mode = "record"          # "record" | "busy"
        self.phase = 0.0
        return self

    def isFlipped(self):
        return True

    def drawRect_(self, rect):
        b = self.bounds()
        w, h = b.size.width, b.size.height
        NSColor.colorWithCalibratedWhite_alpha_(0.04, 0.96).setFill()
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
        NSColor.whiteColor().setFill()
        for i in range(BARS):
            if self.mode == "busy":
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
        return self

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
        if self.timer is None:
            self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1 / 60, self, "tick:", None, True)

    def hide(self):
        NSAnimationContext.beginGrouping()
        NSAnimationContext.currentContext().setDuration_(0.2)
        self.panel.animator().setAlphaValue_(0.0)
        NSAnimationContext.endGrouping()
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None
        self._smooth = [0.0] * BARS
        self.level = 0.0

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


# ─── Main window (WKWebView + JSON bridge) ───────────────────────────────────

class Bridge(NSObject):
    """Receives window.webkit.messageHandlers.app.postMessage({...}) calls."""

    def initWithStore_(self, store):
        self = objc.super(Bridge, self).init()
        if self is None:
            return None
        self.store = store
        self.web = None
        return self

    def userContentController_didReceiveScriptMessage_(self, _ctrl, message):
        msg = dict(message.body())
        kind = msg.get("type")
        if kind == "saveDictionary":
            self.store.save_dictionary(list(msg.get("words", [])))
        elif kind == "saveSnippets":
            self.store.save_snippets({str(k): str(v) for k, v in dict(msg.get("snippets", {})).items()})
        elif kind == "clearHistory":
            self.store.clear_history()
        elif kind == "copy":
            from AppKit import NSPasteboard, NSPasteboardTypeString
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(str(msg.get("text", "")), NSPasteboardTypeString)
            return                      # no re-render, so the "Copied ✓" state stays
        self.push()

    def push(self):
        if self.web is not None:
            data = json.dumps(self.store.state())
            self.web.evaluateJavaScript_completionHandler_(f"window.render({data})", None)


class MainWindow(NSObject):

    def initWithStore_html_(self, store, html_path):
        self = objc.super(MainWindow, self).init()
        if self is None:
            return None
        self.bridge = Bridge.alloc().initWithStore_(store)
        cfg = WKWebViewConfiguration.alloc().init()
        ucc = WKUserContentController.alloc().init()
        ucc.addScriptMessageHandler_name_(self.bridge, "app")
        cfg.setUserContentController_(ucc)

        style = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable
                 | NSWindowStyleMaskResizable | NSWindowStyleMaskFullSizeContentView)
        self.win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 1000, 660), style, NSBackingStoreBuffered, False)
        w = self.win
        w.setTitle_("Dictation")
        w.setTitlebarAppearsTransparent_(True)
        w.setTitleVisibility_(NSWindowTitleHidden)
        w.setMinSize_((760, 520))
        w.setReleasedWhenClosed_(False)
        w.center()

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


def on_main(fn, *args):
    """Run fn on the AppKit main thread (safe to call from any thread)."""
    AppHelper.callAfter(fn, *args)
