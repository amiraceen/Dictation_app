"""
Voice test: the user records a set of phrases in their own voice, then the app
transcribes them and scores how close it got. The same set can be exported and
used to compare speech models (tools/eval_arabic.py --set voice-test.zip).

No AppKit here; recording uses sounddevice, injectable for tests.
"""

import io
import json
import os
import re
import threading
import time
import uuid
import wave
import zipfile

import numpy as np

import arabic

SAMPLE_RATE = 16000

# Everyday dictation, across the dialects we serve. Users delete what they'd never say.
DEFAULT_PHRASES = [
    ("gulf-1", "Gulf", "وين صرت؟ أنا بوصل بعد عشر دقايق إن شاء الله"),
    ("gulf-2", "Gulf", "ممكن ترسل لي الملف قبل العصر؟"),
    ("gulf-3", "Gulf", "خلنا نأجل الاجتماع لبكرة الصبح"),
    ("gulf-4", "Gulf", "الحين مشغول، بكلمك بعدين"),
    ("gulf-5", "Gulf", "شو رايك نطلب غدا من المطعم اللي جنب المكتب؟"),
    ("gulf-6", "Gulf", "أبغى أحجز موعد يوم الأحد الصبح"),
    ("gulf-7", "Gulf", "ترا الفاتورة وصلت، شيك عليها لو سمحت"),
    ("gulf-8", "Gulf", "عساك بخير، شحالك اليوم؟"),
    ("gulf-9", "Gulf", "بغيت أسألك عن الطلبية، متى بتوصل؟"),
    ("msa-1", "MSA", "نود إعلامكم بأن الاجتماع سيعقد يوم الثلاثاء القادم في قاعة المؤتمرات"),
    ("msa-2", "MSA", "يرجى مراجعة المستند وإرسال الملاحظات قبل نهاية الأسبوع"),
    ("msa-3", "MSA", "شكرا لتعاونكم، ونتطلع إلى العمل معكم"),
    ("msa-4", "MSA", "تم تحديث السياسة الجديدة وسيتم تطبيقها من الشهر القادم"),
    ("egy-1", "Egyptian", "أنا هتأخر شوية، الطريق زحمة جدا"),
    ("egy-2", "Egyptian", "عايز أعرف الميعاد اتغير ولا لسه زي ما هو؟"),
    ("egy-3", "Egyptian", "ماشي، هبعتلك الصور بالليل"),
    ("lev-1", "Levantine", "شو بدك ناكل اليوم؟ في مطعم حلو قريب"),
    ("lev-2", "Levantine", "كيفك؟ بدي احكي معك شي ضروري"),
    ("lev-3", "Levantine", "هلق ما بقدر، بتصل فيك بعد شوي"),
    ("mix-1", "Mixed", "ابعث لي الـ presentation على الإيميل"),
    ("mix-2", "Mixed", "عندنا meeting بكرة مع فريق الـ marketing"),
    ("mix-3", "Mixed", "حمل التطبيق من الـ App Store وجربه"),
]


# ─── Scoring ─────────────────────────────────────────────────────────────────

def scoring_words(text):
    """Words for scoring: no diacritics or punctuation, unified alef/yaa/taa marbuta,
    Western digits, lower-case Latin. Applied to both the expected and heard text."""
    text = arabic.normalize(text)
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    text = re.sub(r"(?<!\w)ال\s+(?=[A-Za-z])", "", text)    # "الـ presentation" → "presentation"
    text = re.sub(r"[^\w\s]", " ", text)
    return text.lower().split()


def word_errors(expected, heard):
    """(errors, expected word count): word-level edit distance (substitutions,
    deletions, insertions)."""
    ref, hyp = scoring_words(expected), scoring_words(heard)
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1], len(ref)


def accuracy(errors, words):
    """Share of words right, 0..1 (word error rate turned around, floored at 0)."""
    return max(0.0, 1.0 - errors / words) if words else 0.0


# ─── Storage ─────────────────────────────────────────────────────────────────

def _write_wav(path, samples):
    pcm = (np.clip(np.asarray(samples, dtype=np.float32), -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


def read_wav(path_or_bytes):
    src = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else path_or_bytes
    with wave.open(src) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


class VoiceTestStore:
    """Phrases, their recordings and the latest results, in <data folder>/voice_test/."""

    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, "manifest.json")
        self._lock = threading.Lock()
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}
        self.data.setdefault("phrases", [])
        self.data.setdefault("removed", [])
        self.data.setdefault("results", None)
        known = {p["id"] for p in self.data["phrases"]} | set(self.data["removed"])
        for pid, dialect, text in DEFAULT_PHRASES:
            if pid not in known:
                self.data["phrases"].append({"id": pid, "dialect": dialect, "text": text, "secs": 0})
        self._save()

    def _save(self):
        with open(self.path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(self.path + ".tmp", self.path)

    def _audio_path(self, pid):
        return os.path.join(self.folder, re.sub(r"[^\w-]", "", pid) + ".wav")

    def phrase(self, pid):
        return next((p for p in self.data["phrases"] if p["id"] == pid), None)

    def add(self, text, dialect="Custom"):
        text = str(text).strip()
        if not text:
            return None
        with self._lock:
            p = {"id": "custom-" + uuid.uuid4().hex[:8], "dialect": dialect, "text": text[:500], "secs": 0}
            self.data["phrases"].append(p)
            self._save()
        return p

    def remove(self, pid):
        with self._lock:
            before = len(self.data["phrases"])
            self.data["phrases"] = [p for p in self.data["phrases"] if p["id"] != pid]
            if len(self.data["phrases"]) == before:
                return False
            if not pid.startswith("custom-"):
                self.data["removed"].append(pid)
            try:
                os.remove(self._audio_path(pid))
            except OSError:
                pass
            if self.data["results"]:
                self.data["results"]["per"].pop(pid, None)
            self._save()
            return True

    def save_recording(self, pid, samples):
        with self._lock:
            p = self.phrase(pid)
            if p is None:
                return False
            _write_wav(self._audio_path(pid), samples)
            p["secs"] = round(len(samples) / SAMPLE_RATE, 1)
            if self.data["results"]:
                self.data["results"]["per"].pop(pid, None)      # old result no longer matches
            self._save()
            return True

    def audio_path(self, pid):
        path = self._audio_path(pid)
        return path if os.path.exists(path) else None

    def recorded(self):
        return [p for p in self.data["phrases"] if self.audio_path(p["id"])]

    def set_results(self, model, language, per):
        """per: {pid: {"heard", "errors", "words", "secs"}}"""
        errors = sum(r["errors"] for r in per.values())
        words = sum(r["words"] for r in per.values())
        with self._lock:
            self.data["results"] = {"model": model, "language": language, "when": time.time(),
                                    "accuracy": accuracy(errors, words), "errors": errors, "words": words,
                                    "per": per}
            self._save()

    def state(self):
        with self._lock:
            phrases = [dict(p, recorded=bool(self.audio_path(p["id"]))) for p in self.data["phrases"]]
            return {"phrases": phrases, "results": self.data["results"]}

    def export_zip(self, dest):
        """manifest.json (id, dialect, text, file) + one WAV per recorded phrase."""
        items = []
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for p in self.recorded():
                name = os.path.basename(self._audio_path(p["id"]))
                z.write(self._audio_path(p["id"]), name)
                items.append({"id": p["id"], "dialect": p["dialect"], "text": p["text"], "file": name})
            z.writestr("manifest.json", json.dumps({"phrases": items}, ensure_ascii=False, indent=1))
        return len(items)


def load_zip(path):
    """[(id, dialect, audio, text)] from an exported voice test."""
    out = []
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read("manifest.json"))
        for p in manifest["phrases"]:
            out.append((p["id"], p["dialect"], read_wav(z.read(p["file"])), p["text"]))
    return out


# ─── Recording ───────────────────────────────────────────────────────────────

class PhraseRecorder:
    """Click-to-start, click-to-stop mic recording at 16 kHz mono."""

    def __init__(self, input_stream=None, device=None):
        self._input_stream = input_stream
        self._device = device
        self.phrase_id = None
        self.started = None
        self._stop = threading.Event()
        self._thread = None
        self._frames = []
        self.level = 0.0

    @property
    def active(self):
        return self.phrase_id is not None

    def _open(self):
        if self._input_stream is not None:
            return self._input_stream()
        import sounddevice as sd
        device = self._device() if callable(self._device) else self._device
        return sd.InputStream(device=device, samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=1024)

    def start(self, phrase_id):
        if self.active:
            return False
        self.phrase_id, self.started = phrase_id, time.time()
        self._stop.clear()
        self._frames = []
        self._error = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def _loop(self):
        try:
            with self._open() as stream:
                while not self._stop.is_set():
                    data, _ = stream.read(1024)
                    self._frames.append(np.asarray(data, dtype=np.float32).reshape(-1).copy())
                    self.level = float(np.sqrt(np.mean(self._frames[-1] ** 2)))
        except Exception as e:
            self._error = e

    def stop(self):
        """Returns (phrase_id, samples) or (phrase_id, None) if recording failed."""
        pid = self.phrase_id
        if pid is None:
            return None, None
        self._stop.set()
        self._thread.join(timeout=2)
        self.phrase_id = None
        if self._error is not None or not self._frames:
            return pid, None
        return pid, np.concatenate(self._frames)
