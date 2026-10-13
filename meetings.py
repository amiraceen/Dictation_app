"""
Call start/end detection for the Notetaker. Pure Python, so it can be tested anywhere.
"""


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
