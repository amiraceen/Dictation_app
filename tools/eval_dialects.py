"""Compare speech models on everyday Arabic dialects (Gulf, Egyptian, Levantine, ...).

    python tools/eval_dialects.py --models mlx,hf:openai/whisper-large-v3-turbo --clips 25

Test audio (each set and dialect scored separately; sets that need a login are skipped):
  - Kejue Voice (Saudi, Bahraini, Emirati and other dialect configs), SADA 2022 (Saudi TV,
    everyday speech), Kejue Common Voice, and Casablanca (eight dialects; gated, used only
    if HF_TOKEN is set).
  - FLEURS ar_eg: read Modern Standard Arabic, the same set as tools/eval_arabic.py.

Models:
  mlx                  the app's Accurate model (large-v3-turbo on the GPU) with the app's dialect prompt
  mlx-noprompt         the same model without the prompt
  mlx:<repo>           any MLX Whisper model from Hugging Face (e.g. mlx-community/whisper-large-v3-mlx)
  mlx-noprompt:<repo>  the same, without the dialect prompt
  mlx-hf:<repo>        a Transformers-format fine-tune converted to MLX and run exactly like the app
  mlx-hf-noprompt:<repo>  the same, without the dialect prompt
  hf:<repo>            any Whisper model in Transformers format (fine-tunes), run with PyTorch

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

# Open dialect test sets, tried in order; any that is gated (needs a login) is skipped.
DIALECT_SETS = ["Arabic-STT/kejue-voice", "Arabic-STT/sada2022", "Arabic-STT/kejue-common-voice",
                "Arabic-STT/Casablanca", "MightyStudent/Egyptian-ASR-MGB-3", "Arabic-STT/ASR_Code_Switch"]


def load_dialect_sets(n_clips, repos=DIALECT_SETS, min_s=2.0, max_s=15.0, max_configs=8):
    """{"repo/config": [(id, audio, reference)]}. Streams only the clips it needs."""
    from datasets import get_dataset_config_names, get_dataset_split_names, load_dataset
    sets = {}
    for repo in repos:
        try:
            configs = get_dataset_config_names(repo)
        except Exception as e:
            print(f"  {repo}: skipped ({type(e).__name__}: {str(e)[:120]})", flush=True)
            continue
        for config in configs[:max_configs]:
            name = repo.split("/")[-1] + ("" if config == "default" else f"/{config}")
            try:
                splits = get_dataset_split_names(repo, config)
                split = next((s for s in ("test", "validation", "dev", "train") if s in splits), splits[0])
                ds = load_dataset(repo, config, split=split, streaming=True)
                clips = []
                for i, row in enumerate(ds):
                    text_col = next((c for c in TEXT_COLUMNS if isinstance(row.get(c), str) and row[c].strip()), None)
                    if text_col is None:          # some sets name it differently: take any Arabic text column
                        text_col = next((k for k, v in row.items() if isinstance(v, str)
                                         and any("\u0600" <= ch <= "\u06ff" for ch in v)), None)
                    audio_col = next((k for k, v in row.items() if isinstance(v, dict) and "array" in v), None)
                    if not text_col or not audio_col:
                        print(f"  {name}: columns not recognised: {list(row)}", flush=True)
                        break
                    audio = to_16k(row[audio_col]["array"], row[audio_col]["sampling_rate"])
                    if min_s <= len(audio) / SR <= max_s:
                        clips.append((f"{name}-{i}", audio, row[text_col]))
                    if len(clips) >= n_clips or i > n_clips * 20:
                        break
                if clips:
                    sets[name] = clips
                    print(f"  {name} ({split}, text '{text_col}'): {len(clips)} clips", flush=True)
            except Exception as e:
                print(f"  {name}: skipped ({type(e).__name__}: {str(e)[:120]})", flush=True)
    return sets


def load_fleurs(n_clips):
    import eval_arabic
    return {"MSA (FLEURS)": eval_arabic.load_fleurs(n_clips)}


# ── Models ──

class MlxModel:
    def __init__(self, repo=None, prompt=True, hf_repo=None):
        import tempfile
        import mlx_engine
        folder = tempfile.mkdtemp()
        if hf_repo:
            from huggingface_hub import snapshot_download
            src = snapshot_download(hf_repo, allow_patterns=["config.json", "*.safetensors"])
            mlx_engine.convert_hf(src, folder)
        elif repo:
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
        try:                    # the Mac's GPU when there's room, else the CPU (GitHub's virtual Macs)
            if not torch.backends.mps.is_available():
                raise RuntimeError("no MPS")
            self.pipe = pipeline("automatic-speech-recognition", model=repo, device="mps", dtype=torch.float16)
        except Exception as e:
            print(f"  GPU unavailable ({str(e)[:60]}); using the CPU", flush=True)
            self.pipe = pipeline("automatic-speech-recognition", model=repo, device="cpu", dtype=torch.float32)
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
    if spec.startswith("mlx-noprompt:"):
        return MlxModel(spec[len("mlx-noprompt:"):], prompt=False)
    if spec.startswith(("mlx-hf:", "mlx-hf-noprompt:")):            # a Transformers fine-tune, run the app's way
        return MlxModel(hf_repo=spec.split(":", 1)[1], prompt=spec.startswith("mlx-hf:"))
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


def run_one(spec, sets):
    """Score one model on every set. Returns {set: (wer, cer, secs)} and examples."""
    model = load_model(spec)
    names = list(sets)
    model(sets[names[0]][0][1])                           # warm-up
    row, examples = {}, {}
    for name in names:
        try:
            wer, cer, secs, ex = score(model, sets[name])
        except Exception as e:
            print(f"  {name}: FAILED {type(e).__name__}: {e}", flush=True)
            continue
        row[name], examples[name] = (wer, cer, secs), ex
        print(f"  {name:<22} WER {wer:6.1%}  CER {cer:6.1%}  {secs:.2f}s/clip", flush=True)
    return row, examples


def main():
    import json
    import pickle
    import subprocess
    import tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="mlx,mlx-noprompt")
    ap.add_argument("--clips", type=int, default=25, help="clips per dialect")
    ap.add_argument("--out", default="dialect_results.md")
    ap.add_argument("--one", help=argparse.SUPPRESS)          # internal: score one model, write JSON
    ap.add_argument("--sets", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.one:                                              # child process: one model, then exit
        with open(args.sets, "rb") as f:
            sets = pickle.load(f)
        row, ex = run_one(args.one, sets)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"row": row, "examples": ex}, f, ensure_ascii=False)
        return

    print("Loading test audio…", flush=True)
    sets = load_dialect_sets(args.clips)
    sets.update(load_fleurs(args.clips))
    names = list(sets)
    work = tempfile.mkdtemp()
    sets_path = os.path.join(work, "sets.pkl")
    with open(sets_path, "wb") as f:
        pickle.dump(sets, f)

    table, examples = {}, {}
    for spec in [m.strip() for m in args.models.split(",") if m.strip()]:
        print(f"\n{spec}", flush=True)
        out = os.path.join(work, f"{len(table)}.json")
        # Each model runs in its own process, so the previous one's GPU memory is freed.
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", spec, "--sets", sets_path,
                            "--out", out])
        if r.returncode != 0 or not os.path.exists(out):
            print(f"  FAILED (exit {r.returncode})", flush=True)
            continue
        with open(out, encoding="utf-8") as f:
            res = json.load(f)
        table[spec] = {k: tuple(v) for k, v in res["row"].items()}
        for name, ex in res["examples"].items():
            examples[(spec, name)] = ex

    dial = [n for n in names if n != "MSA (FLEURS)"]
    lines = ["## Arabic dialect accuracy (word errors, lower is better)", "",
             "| Model | " + " | ".join(names) + " | Dialects average | s/clip |",
             "|---|" + "---|" * (len(names) + 2)]
    for spec, row in table.items():
        cells = [f"{row[n][0]:.1%}" if n in row else "–" for n in names]
        avg = [row[n][0] for n in dial if n in row]
        secs = [row[n][2] for n in row]
        lines.append(f"| {spec} | " + " | ".join(cells) + f" | {statistics.mean(avg):.1%} |" if avg
                     else f"| {spec} | " + " | ".join(cells) + " | – |")
        lines[-1] += f" {statistics.median(secs):.2f} |" if secs else " – |"
    lines += ["", f"Up to {args.clips} clips per set. Dialect sets are everyday speech; FLEURS is read formal Arabic.", ""]
    for (spec, name), ex in examples.items():
        lines.append(f"<details><summary>{spec} · {name}</summary>\n")
        lines += [f"- expected: {r}\n  - heard: {h}" for r, h in ex]
        lines.append("\n</details>")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:len(table) + 4]))


if __name__ == "__main__":
    main()
