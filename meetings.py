"""
Meeting logic for the Notetaker: next meeting and countdown, heads-up timing,
and call start/end detection. Pure Python, so it can be tested anywhere.

Events are dicts: {"id", "title", "start", "end", "all_day"} with Unix-time floats.
"""

LOOKAHEAD = 12 * 3600      # show a meeting in the menu bar up to 12 h ahead
NOW_WINDOW = 10 * 60       # a started meeting reads "now" for its first 10 min


def format_countdown(secs):
    """'now', 'in 45s', 'in 12m', 'in 1h 5m'."""
    secs = int(secs)
    if secs <= 0:
        return "now"
    if secs < 60:
        return f"in {secs}s"
    mins = (secs + 59) // 60
    if mins < 60:
        return f"in {mins}m"
    h, m = divmod(mins, 60)
    return f"in {h}h {m}m" if m else f"in {h}h"


def next_meeting(events, now):
    """The meeting to show: one that started in the last 10 min, else the next one today-ish."""
    best = None
    for e in events:
        if e.get("all_day") or e["end"] <= now:
            continue
        if e["start"] <= now and now - e["start"] > NOW_WINDOW:
            continue
        if e["start"] - now > LOOKAHEAD:
            continue
        if best is None or e["start"] < best["start"]:
            best = e
    return best


def menubar_text(event, now, max_title=22):
    if event is None:
        return None
    title = (event.get("title") or "Meeting").strip()
    if len(title) > max_title:
        title = title[:max_title - 1].rstrip() + "…"
    return f"{title} · {format_countdown(event['start'] - now)}"


class MeetingNotifier:
    """Decides when to show the heads-up for a scheduled meeting. Each meeting fires once."""

    GRACE = 60     # still notify if we were asleep/busy and are up to 1 min late

    def __init__(self):
        self._done = set()

    def due(self, events, now, lead):
        if lead < 0:
            return []
        out = []
        for e in events:
            if e.get("all_day"):
                continue
            key = (e["id"], e["start"])
            if key in self._done:
                continue
            if e["start"] - lead <= now < e["start"] + self.GRACE:
                self._done.add(key)
                out.append(e)
        return out


class CallTracker:
    """Turns a noisy 'another app is using the mic' signal into call started/ended events.

    A call starts after the mic has been in use for START_AFTER seconds, and ends
    after it has been idle for END_AFTER seconds (muting or brief reconnects
    shouldn't end it)."""

    START_AFTER = 3.0
    END_AFTER = 15.0

    def __init__(self):
        self.in_call = False
        self.app = None
        self._since = None      # when the signal last flipped away from the current state

    def update(self, active, now, app=None):
        """Feed one sample. Returns 'started', 'ended' or None."""
        if active == self.in_call:
            self._since = None
            if active and app:
                self.app = app
            return None
        if self._since is None:
            self._since = now
        wait = self.START_AFTER if active else self.END_AFTER
        if now - self._since < wait:
            return None
        self._since = None
        self.in_call = active
        if active:
            self.app = app
            return "started"
        return "ended"
