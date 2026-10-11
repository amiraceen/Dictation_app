"""
Notes: plain notes you type or dictate into, and meeting notes the Notetaker
fills with a transcript. One JSON file per note in <data folder>/notes/.

Pure Python (no AppKit) so it can be tested anywhere.
"""

import json
import os
import re
import threading
import time
import uuid


def _fmt_clock(secs):
    secs = int(secs)
    h, m, s = secs // 3600, secs // 60 % 60, secs % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class NotesStore:

    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self._lock = threading.Lock()
        self._notes = {}
        for name in os.listdir(folder):
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(folder, name)) as f:
                    note = json.load(f)
                if isinstance(note, dict) and isinstance(note.get("id"), str):
                    self._notes[note["id"]] = note
            except (OSError, ValueError):
                pass

    # ── persistence ──

    def _path(self, note_id):
        # ids are uuid hex, but never trust them as paths
        return os.path.join(self.folder, re.sub(r"[^0-9a-f]", "", note_id) + ".json")

    def _save(self, note):
        path = self._path(note["id"])
        with open(path + ".tmp", "w") as f:
            json.dump(note, f, ensure_ascii=False)
        os.replace(path + ".tmp", path)

    # ── API ──

    def create(self, title="", meeting=False, now=None):
        now = time.time() if now is None else now
        note = {"id": uuid.uuid4().hex, "title": title or "", "body": "",
                "created": now, "updated": now, "meeting": bool(meeting),
                "transcript": [], "duration": 0.0, "recording": False}
        with self._lock:
            self._notes[note["id"]] = note
            self._save(note)
        return dict(note)

    def get(self, note_id):
        with self._lock:
            note = self._notes.get(note_id)
            return json.loads(json.dumps(note)) if note else None

    def update(self, note_id, title=None, body=None, now=None):
        with self._lock:
            note = self._notes.get(note_id)
            if note is None:
                return False
            if title is not None:
                note["title"] = str(title)[:300]
            if body is not None:
                note["body"] = str(body)
            note["updated"] = time.time() if now is None else now
            self._save(note)
            return True

    def set_recording(self, note_id, recording, duration=None):
        with self._lock:
            note = self._notes.get(note_id)
            if note is None:
                return False
            note["recording"] = bool(recording)
            if duration is not None:
                note["duration"] = round(float(duration), 1)
            self._save(note)
            return True

    def append_transcript(self, note_id, start, text):
        """Add one transcribed chunk; start is seconds from the start of the recording."""
        text = text.strip()
        if not text:
            return False
        with self._lock:
            note = self._notes.get(note_id)
            if note is None:
                return False
            note["transcript"].append({"t": round(float(start), 1), "text": text})
            note["updated"] = time.time()
            self._save(note)
            return True

    def delete(self, note_id):
        with self._lock:
            if self._notes.pop(note_id, None) is None:
                return False
            try:
                os.remove(self._path(note_id))
            except OSError:
                pass
            return True

    def summaries(self):
        """Newest first, without the transcript (for the notes list)."""
        with self._lock:
            out = []
            for n in self._notes.values():
                preview = n["body"].strip() or " ".join(s["text"] for s in n["transcript"][:3])
                out.append({"id": n["id"], "title": n["title"], "created": n["created"],
                            "updated": n["updated"], "meeting": n["meeting"],
                            "duration": n["duration"], "recording": n["recording"],
                            "preview": preview[:160]})
        return sorted(out, key=lambda n: n["created"], reverse=True)

    def recover_interrupted(self):
        """After a crash, notes still marked as recording are not; clear the flag."""
        with self._lock:
            for n in self._notes.values():
                if n["recording"]:
                    n["recording"] = False
                    self._save(n)

    def to_markdown(self, note_id):
        note = self.get(note_id)
        if note is None:
            return ""
        title = note["title"] or "Untitled note"
        when = time.strftime("%A %d %B %Y, %H:%M", time.localtime(note["created"]))
        parts = [f"# {title}", "", when]
        if note["body"].strip():
            parts += ["", "## Notes", "", note["body"].strip()]
        if note["transcript"]:
            parts += ["", "## Transcript", ""]
            parts += [f"[{_fmt_clock(s['t'])}] {s['text']}" for s in note["transcript"]]
        return "\n".join(parts) + "\n"
