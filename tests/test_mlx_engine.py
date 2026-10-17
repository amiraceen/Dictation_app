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

        def __getitem__(self, i):
            return self

    class Model:
        class dims:
            n_mels = 128

        def encoder(self, mel):
            calls.append(("encode",))
            return Arr()

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
    results = []

    def decode(model, features, options):
        calls.append(("decode", options))
        r = results.pop(0) if results else dict(text=" كيفش", no_speech_prob=0.1, avg_logprob=-0.2, compression_ratio=1.1)
        return types.SimpleNamespace(**r)

    class DecodingOptions:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    mod("mlx_whisper.decoding", decode=decode, DecodingOptions=DecodingOptions)
    pkg = mod("mlx_whisper", transcribe=transcribe)
    pkg._results = results
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
        self.assertEqual([c[0] for c in self.calls].count("encode"), 1)   # detection and decoding share it
        opts = self.calls[-1][1]
        self.assertEqual((opts.language, opts.prompt, opts.temperature), ("ar", "هلا", 0.0))
        self.assertFalse(hasattr(opts, "beam_size"))                       # MLX has no beam search

    def test_retries_warmer_when_text_repeats(self):
        m = self.engine.MlxWhisper("/models/turbo")
        sys.modules["mlx_whisper"]._results.extend([
            dict(text=" ha ha ha ha", no_speech_prob=0.1, avg_logprob=-0.3, compression_ratio=3.5),
            dict(text=" أهلين", no_speech_prob=0.1, avg_logprob=-0.3, compression_ratio=1.2)])
        segs, _ = m.transcribe(np.ones(16000, np.float32), language="ar")
        self.assertEqual([s.text for s in segs], [" أهلين"])
        self.assertEqual([c[1].temperature for c in self.calls if c[0] == "decode"], [0.0, 0.2])

    def test_long_recordings_use_full_transcription(self):
        m = self.engine.MlxWhisper("/models/turbo")
        segs, _ = m.transcribe(np.zeros(16000 * 40, np.float32), language="ar", initial_prompt="هلا")
        self.assertEqual(len(list(segs)), 1)
        kw = self.calls[-1][1]
        self.assertEqual((kw["language"], kw["initial_prompt"], kw["path_or_hf_repo"]), ("ar", "هلا", "/models/turbo"))

    def test_silence_gives_nothing(self):
        m = self.engine.MlxWhisper("/models/turbo")
        self.engine.speech_only = lambda audio, ms=300: np.zeros(0, np.float32)
        segs, _ = m.transcribe(np.zeros(16000, np.float32), language="ar")
        self.assertEqual(list(segs), [])
        with self.assertRaises(ValueError):
            m.detect_language(np.zeros(16000, np.float32), vad_filter=True)




class HfConversionNamesTest(unittest.TestCase):
    """Transformers Whisper weight names map onto mlx_whisper's (full check with MLX is in CI)."""

    def test_names(self):
        import mlx_engine
        m = mlx_engine.hf_name_to_mlx
        self.assertEqual(m("model.encoder.layers.3.self_attn.q_proj.weight"), "encoder.blocks.3.attn.query.weight")
        self.assertEqual(m("model.decoder.layers.0.encoder_attn.k_proj.weight"), "decoder.blocks.0.cross_attn.key.weight")
        self.assertEqual(m("model.decoder.layers.0.encoder_attn_layer_norm.bias"), "decoder.blocks.0.cross_attn_ln.bias")
        self.assertEqual(m("model.decoder.layers.1.self_attn_layer_norm.weight"), "decoder.blocks.1.attn_ln.weight")
        self.assertEqual(m("model.encoder.layers.0.final_layer_norm.weight"), "encoder.blocks.0.mlp_ln.weight")
        self.assertEqual(m("model.encoder.layers.0.fc2.bias"), "encoder.blocks.0.mlp2.bias")
        self.assertEqual(m("model.decoder.embed_tokens.weight"), "decoder.token_embedding.weight")
        self.assertEqual(m("model.decoder.embed_positions.weight"), "decoder.positional_embedding")
        self.assertEqual(m("model.encoder.layer_norm.weight"), "encoder.ln_post.weight")
        self.assertEqual(m("model.decoder.layer_norm.bias"), "decoder.ln.bias")
        self.assertIsNone(m("proj_out.weight"))
        self.assertIsNone(m("model.encoder.embed_positions.weight"))
        cfg = mlx_engine.hf_config_to_mlx({"num_mel_bins": 128, "max_source_positions": 1500, "d_model": 1280,
                                           "encoder_attention_heads": 20, "encoder_layers": 32, "vocab_size": 51866,
                                           "max_target_positions": 448, "decoder_attention_heads": 20,
                                           "decoder_layers": 4})
        self.assertEqual((cfg["n_mels"], cfg["n_text_layer"], cfg["n_vocab"]), (128, 4, 51866))

if __name__ == "__main__":
    unittest.main()
