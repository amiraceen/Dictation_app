"""The MLX (graphics chip) engine wrapper, with stand-ins for MLX so it runs anywhere."""

import os
import sys
import types
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _stub_mlx(calls):
    def mod(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m
        return m

    class Arr:
        def astype(self, dtype):
            return self

    class Model:
        class dims:
            n_mels = 128

        def detect_language(self, mel):
            return None, {"he": 0.5, "ar": 0.3, "en": 0.2}

    class ModelHolder:
        @classmethod
        def get_model(cls, path, dtype):
            calls.append(("load", path))
            return Model()

    def transcribe(audio, **kw):
        calls.append(("transcribe", kw))
        return {"segments": [{"text": " كيفش", "no_speech_prob": 0.1, "avg_logprob": -0.2,
                              "compression_ratio": 1.1}]}

    mlx = mod("mlx")
    mlx.core = mod("mlx.core", float16="f16", array=lambda x: x, eval=lambda *a: None)
    pkg = mod("mlx_whisper", transcribe=transcribe)
    pkg.transcribe = transcribe
    mod("mlx_whisper.transcribe", ModelHolder=ModelHolder)
    mod("mlx_whisper.audio", N_FRAMES=3000, N_SAMPLES=480000,
        log_mel_spectrogram=lambda audio, n_mels, padding: Arr(), pad_or_trim=lambda m, n, axis: m)


class MlxEngineTest(unittest.TestCase):

    def setUp(self):
        self.saved = {k: v for k, v in sys.modules.items() if k == "mlx" or k.startswith(("mlx.", "mlx_whisper"))}
        self.calls = []
        _stub_mlx(self.calls)
        import mlx_engine
        self.engine = mlx_engine
        self.orig_vad = mlx_engine.speech_only
        mlx_engine.speech_only = lambda audio, ms=300: audio

    def tearDown(self):
        self.engine.speech_only = self.orig_vad
        for k in [k for k in sys.modules if k == "mlx" or k.startswith(("mlx.", "mlx_whisper"))]:
            del sys.modules[k]
        sys.modules.update(self.saved)

    def test_like_faster_whisper(self):
        m = self.engine.MlxWhisper("/models/turbo")
        self.assertEqual(self.calls[0], ("load", "/models/turbo"))
        self.assertIn("mlx_whisper.timing", sys.modules)                 # numba/SciPy stand-in
        lang, p, probs = m.detect_language(np.zeros(16000, np.float32), vad_filter=True)
        self.assertEqual((lang, probs[1]), ("he", ("ar", 0.3)))
        segs, _ = m.transcribe(np.zeros(16000, np.float32), language="ar", initial_prompt="هلا",
                               vad_filter=True, vad_parameters=dict(min_silence_duration_ms=300), beam_size=5)
        seg = list(segs)[0]
        self.assertEqual((seg.text, seg.no_speech_prob), (" كيفش", 0.1))
        kw = self.calls[-1][1]
        self.assertEqual((kw["language"], kw["initial_prompt"], kw["path_or_hf_repo"]), ("ar", "هلا", "/models/turbo"))
        self.assertNotIn("beam_size", kw)                                   # MLX has no beam search

    def test_silence_gives_nothing(self):
        m = self.engine.MlxWhisper("/models/turbo")
        self.engine.speech_only = lambda audio, ms=300: np.zeros(0, np.float32)
        segs, _ = m.transcribe(np.zeros(16000, np.float32), language="ar")
        self.assertEqual(list(segs), [])
        with self.assertRaises(ValueError):
            m.detect_language(np.zeros(16000, np.float32), vad_filter=True)


if __name__ == "__main__":
    unittest.main()
