"""
Whisper on the Mac's graphics chip (Apple MLX), for the "Accurate" model.

Every Apple-silicon Mac (M1 or newer, MacBook Air included) has a GPU that runs
large-v3-turbo several times faster than the CPU. This class mimics the parts of
faster-whisper's WhisperModel that the app uses (detect_language, transcribe), so
DictationCore doesn't care which engine it has.
"""

import hashlib
import sys
import types

import numpy as np

SAMPLE_RATE = 16000
WINDOW = 30 * SAMPLE_RATE           # Whisper hears 30 s at a time
MLX_REPO = "mlx-community/whisper-large-v3-turbo"
TEMPERATURES = (0.0, 0.2, 0.4, 0.6)  # retry warmer when the greedy result looks broken


def _skip_word_timings():
    """mlx_whisper imports its word-timestamp module (numba + SciPy, ~100 MB) at start-up.
    Kalam never asks for word timestamps, so a stand-in keeps those out of the app."""
    name = "mlx_whisper.timing"
    if name not in sys.modules:
        stub = types.ModuleType(name)

        def add_word_timestamps(*a, **kw):
            raise RuntimeError("word timestamps are not included in Kalam")

        stub.add_word_timestamps = add_word_timestamps
        sys.modules[name] = stub


def available():
    """True when MLX can run here (Apple silicon with Metal)."""
    try:
        import mlx.core as mx
        mx.eval(mx.array([1.0]) + 1)
        return True
    except Exception:
        return False


class _Segment:
    __slots__ = ("text", "no_speech_prob", "avg_logprob", "compression_ratio")

    def __init__(self, d):
        self.text = d.get("text", "")
        self.no_speech_prob = d.get("no_speech_prob", 0.0)
        self.avg_logprob = d.get("avg_logprob", 0.0)
        self.compression_ratio = d.get("compression_ratio", 1.0)


def speech_only(audio, min_silence_ms=300):
    """Keep only the parts with speech (Silero VAD from faster-whisper), so silence
    can't turn into made-up words. Returns an empty array when nobody spoke."""
    from faster_whisper.vad import VadOptions, collect_chunks, get_speech_timestamps
    chunks = get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=min_silence_ms))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    parts, _ = collect_chunks(audio, chunks)
    return np.concatenate(parts).astype(np.float32)


class MlxWhisper:
    def __init__(self, path):
        _skip_word_timings()
        import mlx.core as mx
        from mlx_whisper.transcribe import ModelHolder
        self.path = str(path)
        self._mx = mx
        self.model = ModelHolder.get_model(self.path, mx.float16)    # loads once, then cached
        self._cached = (None, None)          # (audio fingerprint, encoder output)

    def _features(self, audio):
        """Encoder output for up to 30 s of audio. The encoder is most of the work, so the
        result is kept: language detection and transcription of the same clip share it."""
        key = hashlib.blake2b(np.ascontiguousarray(audio, dtype=np.float32).tobytes(), digest_size=16).digest()
        if self._cached[0] == key:
            return self._cached[1]
        from mlx_whisper.audio import N_FRAMES, N_SAMPLES, log_mel_spectrogram, pad_or_trim
        mel = log_mel_spectrogram(audio, n_mels=self.model.dims.n_mels, padding=N_SAMPLES)
        mel = pad_or_trim(mel, N_FRAMES, axis=-2).astype(self._mx.float16)
        features = self.model.encoder(mel[None])[0]
        self._cached = (key, features)
        return features

    def detect_language(self, audio, vad_filter=False, vad_parameters=None):
        """(language, probability, [(code, p), ...]) like faster-whisper."""
        if vad_filter:
            audio = speech_only(audio)
        if len(audio) == 0:
            raise ValueError("no speech")
        _, probs = self.model.detect_language(self._features(audio[:WINDOW]))
        ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[0][0], ranked[0][1], ranked

    def transcribe(self, audio, language=None, initial_prompt=None, vad_filter=True,
                   vad_parameters=None, beam_size=None, **_):
        """(segments, None) like faster-whisper. MLX decodes greedily (no beam search)."""
        import mlx_whisper
        if vad_filter:
            ms = (vad_parameters or {}).get("min_silence_duration_ms", 300)
            audio = speech_only(audio, ms)
        if len(audio) < SAMPLE_RATE // 10:
            return iter(()), None
        if len(audio) <= WINDOW:                 # a dictation: one window, encoder output reused
            return iter(self._decode_window(audio, language, initial_prompt)), None
        out = mlx_whisper.transcribe(
            audio, path_or_hf_repo=self.path, language=language, initial_prompt=initial_prompt,
            condition_on_previous_text=False, verbose=None, fp16=True)
        return iter([_Segment(s) for s in out.get("segments", [])]), None


    def _decode_window(self, audio, language, prompt):
        """Decode one ≤30 s window from the shared encoder output, with Whisper's usual
        fallback: retry at a higher temperature if the text repeats itself or is unlikely."""
        from mlx_whisper.decoding import DecodingOptions, decode
        features = self._features(audio)
        result = None
        for t in TEMPERATURES:
            result = decode(self.model, features, DecodingOptions(
                language=language, prompt=prompt, temperature=t, fp16=True))
            if result.no_speech_prob > 0.6 and result.avg_logprob < -1.0:
                return []                        # silence
            if result.compression_ratio <= 2.4 and result.avg_logprob >= -1.0:
                break
        return [_Segment({"text": result.text, "no_speech_prob": result.no_speech_prob,
                          "avg_logprob": result.avg_logprob, "compression_ratio": result.compression_ratio})]


def download(folder):
    """Fetch the MLX weights (config.json + weights.safetensors, about 1.6 GB)."""
    from huggingface_hub import snapshot_download
    snapshot_download(MLX_REPO, local_dir=folder, allow_patterns=["config.json", "weights.*"])
