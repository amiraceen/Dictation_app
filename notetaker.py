"""
Notetaker: records a meeting (your mic, plus other participants through system
audio when available), cuts the audio into chunks at natural pauses, and
transcribes each chunk in the background so the transcript appears live.

No AppKit here; the system-audio source and transcriber are passed in.
"""

import queue
import threading
import time

import numpy as np

SAMPLE_RATE = 16000
BLOCK = 1024


class Chunker:
    """Collects mono audio and cuts it into chunks, preferring pauses.

    A chunk ends at the first pause after min_secs, or at the quietest moment
    between min_secs and max_secs if nobody pauses."""

    FRAME = 1600          # 0.1 s analysis frames

    def __init__(self, sr=SAMPLE_RATE, min_secs=6.0, max_secs=20.0, pause_secs=0.6, quiet_rms=0.006):
        self.sr, self.quiet_rms = sr, quiet_rms
        self.min_n, self.max_n = int(min_secs * sr), int(max_secs * sr)
        self.pause_frames = max(1, int(pause_secs * sr / self.FRAME))
        self._buf = []
        self._n = 0
        self._start = 0           # samples since recording start where the buffer begins

    def _rms_frames(self, audio):
        n = len(audio) // self.FRAME
        if n == 0:
            return np.zeros(0)
        return np.sqrt(np.mean(audio[:n * self.FRAME].reshape(n, self.FRAME) ** 2, axis=1))

    def feed(self, samples):
        """Add samples; return a list of (start_secs, audio) chunks that are ready."""
        self._buf.append(np.asarray(samples, dtype=np.float32).reshape(-1))
        self._n += len(self._buf[-1])
        out = []
        while self._n >= self.min_n:
            audio = np.concatenate(self._buf)
            rms = self._rms_frames(audio)
            cut = None
            # Pause = pause_frames consecutive quiet frames ending at/after min_n.
            quiet = rms < self.quiet_rms
            run = 0
            for i, q in enumerate(quiet):
                run = run + 1 if q else 0
                if run >= self.pause_frames and (i + 1) * self.FRAME >= self.min_n:
                    cut = (i + 1) * self.FRAME
                    break
            if cut is None and len(audio) >= self.max_n:
                lo, hi = self.min_n // self.FRAME, self.max_n // self.FRAME
                cut = (lo + int(np.argmin(rms[lo:hi]))) * self.FRAME if hi > lo else self.max_n
            if cut is None:
                self._buf, self._n = [audio], len(audio)
                break
            out.append((self._start / self.sr, audio[:cut]))
            self._start += cut
            rest = audio[cut:]
            self._buf, self._n = [rest], len(rest)
        return out

    def flush(self):
        if self._n == 0:
            return None
        audio = np.concatenate(self._buf)
        chunk = (self._start / self.sr, audio)
        self._start += len(audio)
        self._buf, self._n = [], 0
        return chunk

    def is_silent(self, audio):
        rms = self._rms_frames(audio)
        return rms.size == 0 or float(rms.max()) < self.quiet_rms


class Mixer:
    """Mixes system audio into the mic stream. The mic is the clock: for every mic
    block we take the same number of system samples, padding with silence if
    system audio is late, and dropping backlog beyond max_lag."""

    def __init__(self, sr=SAMPLE_RATE, max_lag=1.0):
        self._lock = threading.Lock()
        self._sys = np.zeros(0, dtype=np.float32)
        self._max = int(sr * max_lag)

    def push_system(self, samples):
        with self._lock:
            self._sys = np.concatenate([self._sys, np.asarray(samples, dtype=np.float32).reshape(-1)])
            if len(self._sys) > self._max:
                self._sys = self._sys[-self._max:]

    def mix(self, mic):
        mic = np.asarray(mic, dtype=np.float32).reshape(-1)
        with self._lock:
            take = self._sys[:len(mic)]
            self._sys = self._sys[len(take):]
        if len(take) < len(mic):
            take = np.concatenate([take, np.zeros(len(mic) - len(take), dtype=np.float32)])
        return np.clip(mic + take, -1.0, 1.0)


class Notetaker:
    """One meeting recording at a time. Callbacks run on background threads.

    transcribe(audio) -> str
    on_segment(note_id, start_secs, text)
    on_warning(note_id, secs_left)
    on_stopped(note_id, duration_secs, reason)       reason: "user" | "max_length" | "error"
    on_level(rms)
    system_audio: optional factory(on_samples, on_error) -> object with start()/stop()
    """

    WARN_BEFORE = 120      # warn 2 minutes before the maximum length

    def __init__(self, transcribe, on_segment, on_stopped, on_warning=None, on_level=None,
                 on_error=None, input_stream=None, system_audio=None, device=None):
        self.transcribe = transcribe
        self.on_segment = on_segment
        self.on_stopped = on_stopped
        self.on_warning = on_warning or (lambda note_id, secs: None)
        self.on_level = on_level or (lambda rms: None)
        self.on_error = on_error or (lambda msg: None)
        self._input_stream = input_stream
        self._system_audio = system_audio
        self._device = device
        self._lock = threading.Lock()
        self.active = False
        self.note_id = None
        self.started = None
        self._stop_reason = None

    def elapsed(self):
        return time.monotonic() - self.started if self.active and self.started else 0.0

    def start(self, note_id, max_secs, capture_system=True):
        with self._lock:
            if self.active:
                return False
            self.active = True
            self.note_id = note_id
            self.started = time.monotonic()
            self._stop_reason = None
        self._max_secs = max_secs
        self._queue = queue.Queue()
        self._mixer = Mixer()
        self._sys = None
        if capture_system and self._system_audio is not None:
            try:
                self._sys = self._system_audio(self._mixer.push_system, self.on_error)
                self._sys.start()
            except Exception as e:           # no permission, old macOS, …: mic only
                self._sys = None
                self.on_error(f"System audio unavailable: {e}")
        self._worker = threading.Thread(target=self._transcribe_loop, args=(note_id,), daemon=True)
        self._worker.start()
        threading.Thread(target=self._record_loop, args=(note_id,), daemon=True).start()
        return True

    def stop(self, reason="user"):
        with self._lock:
            if self.active and self._stop_reason is None:
                self._stop_reason = reason

    def _open_stream(self):
        if self._input_stream is not None:
            return self._input_stream()
        import sounddevice as sd
        return sd.InputStream(device=self._device() if callable(self._device) else self._device,
                              samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=BLOCK)

    def _record_loop(self, note_id):
        chunker = Chunker()
        warned = False
        reason = "user"
        try:
            with self._open_stream() as stream:
                while self._stop_reason is None:
                    data, _ = stream.read(BLOCK)
                    mixed = self._mixer.mix(data)
                    self.on_level(float(np.sqrt(np.mean(mixed ** 2))))
                    for chunk in chunker.feed(mixed):
                        self._queue.put(chunk)
                    elapsed = self.elapsed()
                    if not warned and elapsed >= self._max_secs - self.WARN_BEFORE:
                        warned = True
                        self.on_warning(note_id, max(0, self._max_secs - elapsed))
                    if elapsed >= self._max_secs:
                        self.stop("max_length")
            reason = self._stop_reason or "user"
        except Exception as e:
            reason = "error"
            self.on_error(f"Mic error: {e}")
        finally:
            if self._sys is not None:
                try:
                    self._sys.stop()
                except Exception:
                    pass
            last = chunker.flush()
            if last is not None:
                self._queue.put(last)
            duration = self.elapsed()
            self._queue.put(None)            # tells the worker to finish
            self._worker.join()
            with self._lock:
                self.active = False
                self.note_id = None
                self.started = None
            self.on_stopped(note_id, duration, reason)

    def _transcribe_loop(self, note_id):
        chunker = Chunker()
        while True:
            item = self._queue.get()
            if item is None:
                return
            start, audio = item
            if len(audio) < SAMPLE_RATE * 0.3 or chunker.is_silent(audio):
                continue
            try:
                text = self.transcribe(audio)
            except Exception as e:
                self.on_error(f"Transcription error: {e}")
                continue
            if text and text.strip():
                self.on_segment(note_id, start, text.strip())
