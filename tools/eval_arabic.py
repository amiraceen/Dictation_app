"""Measure Arabic dictation accuracy and speed for different Whisper models.

    python tools/eval_arabic.py --models small,large-v3-turbo --clips 40 --out results.md

Test audio: Google FLEURS Arabic (ar_eg, CC-BY-4.0): read Modern Standard Arabic
with an Egyptian accent. Clips are chosen to be dictation-length (3-15 s).

For each model it reports:
  WER  word error rate  (lower is better; 10% = 1 word in 10 wrong)
  CER  character error rate
  time median seconds per clip on this machine
Both the model output and the reference are normalised first (no diacritics or
punctuation, unified alef/yaa/taa marbuta, Western digits) so only words count.
"""

import argparse
import csv
import io
import os
import re
import statistics
import sys
import tarfile
import time
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import arabic  # noqa: E402,F401
import voicetest  # noqa: E402

ARABIC_PROMPT = "مرحبا، كيف حالك؟ هذا نص عربي مكتوب بعلامات الترقيم."


def normalize_for_scoring(text):
    """Standard Arabic ASR scoring normalisation (applied to both sides); same as the app's voice test."""
    return " ".join(voicetest.scoring_words(text))


def load_fleurs(n_clips, min_s=3.0, max_s=15.0):
    from huggingface_hub import hf_hub_download
    tsv = hf_hub_download("google/fleurs", "data/ar_eg/test.tsv", repo_type="dataset")
    tar = hf_hub_download("google/fleurs", "data/ar_eg/audio/test.tar.gz", repo_type="dataset")
    refs = {}
    with open(tsv, encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(row) >= 3:
                refs[row[1]] = row[2]                # file_name -> raw transcription
    clips = []
    with tarfile.open(tar) as t:
        for member in sorted(t.getmembers(), key=lambda m: m.name):
            name = os.path.basename(member.name)
            if not member.isfile() or name not in refs:
                continue
            data = t.extractfile(member).read()
            with wave.open(io.BytesIO(data)) as w:
                assert w.getframerate() == 16000 and w.getnchannels() == 1
                audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            if min_s <= len(audio) / 16000 <= max_s:
                clips.append((name, audio, refs[name]))
            if len(clips) >= n_clips:
                break
    return clips


def transcribe(model, audio, language, prompt):
    segs, _ = model.transcribe(audio, language=language, initial_prompt=prompt, beam_size=5,
                               vad_filter=True, vad_parameters=dict(min_silence_duration_ms=300))
    return " ".join(s.text for s in segs).strip()


def evaluate(model_id, clips, language="ar", prompt=None, label=None):
    import jiwer
    from faster_whisper import WhisperModel
    t0 = time.perf_counter()
    model = WhisperModel(model_id, device="cpu", compute_type="int8")
    load_s = time.perf_counter() - t0
    transcribe(model, clips[0][1], language, prompt)              # warm-up
    hyps, refs, times = [], [], []
    for _, audio, ref in clips:
        t = time.perf_counter()
        hyp = transcribe(model, audio, language, prompt)
        times.append(time.perf_counter() - t)
        hyps.append(normalize_for_scoring(hyp) or "-")
        refs.append(normalize_for_scoring(ref))
    return {"label": label or model_id, "wer": jiwer.wer(refs, hyps), "cer": jiwer.cer(refs, hyps),
            "time": statistics.median(times), "load": load_s,
            "examples": list(zip(refs[:3], hyps[:3]))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="small,medium,large-v3-turbo,large-v3")
    ap.add_argument("--clips", type=int, default=40)
    ap.add_argument("--out", default="arabic_results.md")
    ap.add_argument("--set", default="",
                    help="score an exported voice test (voice-test.zip) instead of FLEURS")
    ap.add_argument("--prompt-test", default="large-v3-turbo",
                    help="also run this model with an Arabic initial prompt ('' to skip)")
    args = ap.parse_args()

    if args.set:
        clips = [(pid, audio, text) for pid, _, audio, text in voicetest.load_zip(args.set)]
        source = f"voice test {os.path.basename(args.set)}"
    else:
        clips = load_fleurs(args.clips)
        source = "FLEURS ar_eg"
    secs = sum(len(a) for _, a, _ in clips) / 16000
    print(f"{len(clips)} {source} clips, {secs:.0f} s of audio", flush=True)

    runs = [(m, None, m) for m in args.models.split(",") if m]
    if args.prompt_test:
        runs.append((args.prompt_test, ARABIC_PROMPT, f"{args.prompt_test} + Arabic prompt"))
    results = []
    for model_id, prompt, label in runs:
        try:
            r = evaluate(model_id, clips, prompt=prompt, label=label)
        except Exception as e:                                   # keep going if one model fails
            print(f"{label}: FAILED {e}", flush=True)
            continue
        results.append(r)
        print(f"{label:<34} WER {r['wer']:.1%}  CER {r['cer']:.1%}  {r['time']:.2f}s/clip", flush=True)

    lines = [f"## Arabic dictation accuracy ({len(clips)} {source} clips, {secs:.0f} s, language=ar)", "",
             "| Model | Word errors (WER) | Character errors (CER) | Seconds per clip (CPU) |",
             "|---|---|---|---|"]
    lines += [f"| {r['label']} | {r['wer']:.1%} | {r['cer']:.1%} | {r['time']:.2f} |" for r in results]
    lines += ["", "Seconds are on this build machine's CPU (a slow 3-core virtual Mac); "
              "a real Mac is faster, and the Mac's graphics chip faster still.", ""]
    for r in results:
        lines += [f"<details><summary>{r['label']}: examples</summary>", ""]
        lines += [f"- ref: {ref}\n  - got: {hyp}" for ref, hyp in r["examples"]]
        lines += ["", "</details>"]
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:len(results) + 4]))


if __name__ == "__main__":
    main()
