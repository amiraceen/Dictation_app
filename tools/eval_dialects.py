"""Compare speech models on everyday Arabic dialects (Gulf, Egyptian, Levantine, ...).

    python tools/eval_dialects.py --models mlx,hf:openai/whisper-large-v3-turbo --clips 25

Test audio:
  - Casablanca (Arabic-STT/Casablanca on Hugging Face): spontaneous speech in eight dialects,
    including the UAE, Egypt, Jordan, Palestine and Yemen. Each dialect is scored separately.
  - FLEURS ar_eg: read Modern Standard Arabic, the same set as tools/eval_arabic.py.

Models:
  mlx                  the app's Accurate model (large-v3-turbo on the GPU) with the app's dialect prompt
  mlx-noprompt         the same model without the prompt
  mlx:<repo>           any MLX Whisper model from Hugging Face (e.g. mlx-community/whisper-large-v3-mlx)
  hf:<repo>            any Whisper model in Transformers format (fine-tunes), run with PyTorch on the GPU

Prints a table of word error rate (WER) per dialect; lower is better.
"""

import argparse
import os
import statistics
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import arabic  # noqa: E402
import voicetest  # noqa: E402

SR = 16000
TEXT_COLUMNS = ("transcription", "text", "sentence", "transcript", "normalized_text", "raw_transcription")


def words(text):
    return " ".join(voicetest.scoring_words(text))


def to_16k(array, sr):
    audio = np.asarray(array, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SR:
        n = int(len(audio) * SR / sr)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)
    return audio


# ── Test sets ──

def load_casablanca(n_clips, min_s=2.0, max_s=15.0):
    """{dialect: [(id, audio, reference)]}. Streams only the clips it needs."""
    from datasets import get_dataset_config_names, get_dataset_split_names, load_dataset
    repo = "Arabic-STT/Casablanca"
    sets = {}
    for config in get_dataset_config_names(repo):
        try:
            splits = get_dataset_split_names(repo, config)
            split = next((s for s in ("test", "validation", "dev", "train") if s in splits), splits[0])
            ds = load_dataset(repo, config, split=split, streaming=True)
            clips = []
            for i, row in enumerate(ds):
                text_col = next((c for c in TEXT_COLUMNS if isinstance(row.get(c), str) and row[c].strip()), None)
                audio_col = next((k for k, v in row.items() if isinstance(v, dict) and "array" in v), None)
                if not text_col or not audio_col:
                    print(f"  {config}: columns not recognised: {list(row)}", flush=True)
                    break
                audio = to_16k(row[audio_col]["array"], row[audio_col]["sampling_rate"])
                if min_s <= len(audio) / SR <= max_s:
                    clips.append((f"{config}-{i}", audio, row[text_col]))
                if len(clips) >= n_clips or i > n_clips * 20:
                    break
            if clips:
                sets[config] = clips
                print(f"  Casablanca {config} ({split}): {len(clips)} clips", flush=True)
        except Exception as e:
            print(f"  Casablanca {config}: skipped ({type(e).__name__}: {e})", flush=True)
    return sets


def load_fleurs(n_clips):
    import eval_arabic
    return {"MSA (FLEURS)": eval_arabic.load_fleurs(n_clips)}


# ── Models ──

class MlxModel:
    def __init__(self, repo=None, prompt=True):
        import tempfile
        import mlx_engine
        folder = tempfile.mkdtemp()
        if repo:
            from huggingface_hub import snapshot_download
            snapshot_download(repo, local_dir=folder, allow_patterns=["config.json", "weights.*", "*.npz"])
        else:
            mlx_engine.download(folder)
        self.m = mlx_engine.MlxWhisper(folder)
        self.prompt = arabic.initial_prompt("ar", (), True) if prompt else None

    def __call__(self, audio):
        segs, _ = self.m.transcribe(audio, language="ar", initial_prompt=self.prompt)
        return " ".join(s.text for s in segs)


class HfModel:
    """A Transformers Whisper checkpoint (most published fine-tunes) on the Mac's GPU."""

    def __init__(self, repo):
        import torch
        from transformers import pipeline
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        self.pipe = pipeline("automatic-speech-recognition", model=repo, device=dev,
                             torch_dtype=torch.float16 if dev == "mps" else torch.float32)
        self.kwargs = {"language": "ar", "task": "transcribe"}

    def __call__(self, audio):
        import mlx_engine
        audio = mlx_engine.speech_only(audio)              # same silence trimming as the app
        if len(audio) < SR // 10:
            return ""
        try:
            return self.pipe({"raw": audio, "sampling_rate": SR}, generate_kwargs=self.kwargs)["text"]
        except Exception:
            if not self.kwargs:
                raise
            self.kwargs = {}                               # older fine-tunes don't accept language=
            return self.pipe({"raw": audio, "sampling_rate": SR})["text"]


def load_model(spec):
    if spec == "mlx":
        return MlxModel()
    if spec == "mlx-noprompt":
        return MlxModel(prompt=False)
    if spec.startswith("mlx:"):
        return MlxModel(spec[4:], prompt=True)
    if spec.startswith("hf:"):
        return HfModel(spec[3:])
    raise ValueError(f"unknown model {spec}")


def score(model, clips):
    import jiwer
    refs, hyps, times = [], [], []
    for _, audio, ref in clips:
        t = time.perf_counter()
        hyp = model(audio)
        times.append(time.perf_counter() - t)
        refs.append(words(ref) or "-")
        hyps.append(words(hyp) or "-")
    return jiwer.wer(refs, hyps), jiwer.cer(refs, hyps), statistics.median(times), list(zip(refs, hyps))[:2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="mlx,mlx-noprompt")
    ap.add_argument("--clips", type=int, default=25, help="clips per dialect")
    ap.add_argument("--out", default="dialect_results.md")
    args = ap.parse_args()

    print("Loading test audio…", flush=True)
    sets = load_casablanca(args.clips)
    sets.update(load_fleurs(args.clips))
    names = list(sets)

    table = {}
    examples = {}
    for spec in [m.strip() for m in args.models.split(",") if m.strip()]:
        print(f"\n{spec}", flush=True)
        try:
            model = load_model(spec)
            model(sets[names[0]][0][1])                    # warm-up
        except Exception as e:
            print(f"  FAILED to load: {type(e).__name__}: {e}", flush=True)
            continue
        table[spec] = {}
        for name in names:
            try:
                wer, cer, secs, ex = score(model, sets[name])
            except Exception as e:
                print(f"  {name}: FAILED {type(e).__name__}: {e}", flush=True)
                continue
            table[spec][name] = (wer, cer, secs)
            examples[(spec, name)] = ex
            print(f"  {name:<22} WER {wer:6.1%}  CER {cer:6.1%}  {secs:.2f}s/clip", flush=True)
        del model

    dial = [n for n in names if n != "MSA (FLEURS)"]
    lines = ["## Arabic dialect accuracy (word errors, lower is better)", "",
             "| Model | " + " | ".join(names) + " | Dialects average | s/clip |",
             "|---|" + "---|" * (len(names) + 2)]
    for spec, row in table.items():
        cells = [f"{row[n][0]:.0%}" if n in row else "–" for n in names]
        avg = [row[n][0] for n in dial if n in row]
        secs = [row[n][2] for n in row]
        lines.append(f"| {spec} | " + " | ".join(cells) +
                     f" | {statistics.mean(avg):.0%} | {statistics.median(secs):.2f} |" if avg and secs
                     else f"| {spec} | " + " | ".join(cells) + " | – | – |")
    lines += ["", f"{args.clips} clips per set. Casablanca is spontaneous dialect speech; FLEURS is read formal Arabic.", ""]
    for (spec, name), ex in examples.items():
        lines.append(f"<details><summary>{spec} · {name}</summary>\n")
        lines += [f"- expected: {r}\n  - heard: {h}" for r, h in ex]
        lines.append("\n</details>")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:len(table) + 4]))


if __name__ == "__main__":
    main()
