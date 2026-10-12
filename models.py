"""
Speech models: the built-in Whisper "small" (CPU) and an optional, more accurate
large-v3-turbo that runs on the Mac's graphics chip (MLX). The accurate one is downloaded
once into the app's data folder and then works offline. No AppKit here.
"""

import os
import shutil
import threading

MODELS = {
    # choice: (folder / faster-whisper name, label, download size in bytes or 0 if built in, engine)
    "small": ("small", "Whisper small", 0, "cpu"),
    "turbo": ("whisper-large-v3-turbo-mlx", "Whisper large-v3-turbo", 1_620_000_000, "mlx"),
}
LEGACY_FOLDERS = ("large-v3-turbo",)      # CPU turbo from an earlier build: too slow, removed
MODEL_OPTIONS = [("small", "Fast · built in"), ("turbo", "Accurate · 1.6 GB download")]
_DONE = ".complete"


def _folder_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _hf_download(choice, folder):
    import mlx_engine
    mlx_engine.download(folder)


class ModelStore:
    """Where each model lives and whether it's ready; downloads in the background."""

    def __init__(self, folder, builtin_path=None, downloader=_hf_download):
        self.folder = folder
        self.builtin_path = builtin_path      # bundled "small" inside the app, or None (download/cache)
        self._download = downloader
        self.downloading = None               # choice being downloaded
        self.error = None
        self._thread = None
        for name in LEGACY_FOLDERS:
            shutil.rmtree(os.path.join(folder, name), ignore_errors=True)

    def _dir(self, choice):
        return os.path.join(self.folder, MODELS[choice][0])

    def label(self, choice):
        return MODELS[choice][1]

    def engine(self, choice):
        return MODELS[choice][3]

    def ready(self, choice):
        if MODELS[choice][2] == 0:
            return True
        return os.path.exists(os.path.join(self._dir(choice), _DONE))

    def path(self, choice):
        """What to hand to WhisperModel: a folder, or a model name it can fetch itself."""
        if MODELS[choice][2] == 0:
            return self.builtin_path or MODELS[choice][0]
        return self._dir(choice)

    def progress(self):
        """0..1 for the running download, else None."""
        if not self.downloading:
            return None
        size = MODELS[self.downloading][2]
        return min(0.99, _folder_size(self._dir(self.downloading)) / size)

    def download(self, choice, on_done):
        """Start fetching `choice` (resumes a partial download). on_done(ok) runs on the worker."""
        if self.ready(choice):
            on_done(True)
            return
        if self.downloading:
            return
        self.downloading, self.error = choice, None

        def work():
            ok = False
            try:
                os.makedirs(self._dir(choice), exist_ok=True)
                self._download(choice, self._dir(choice))
                open(os.path.join(self._dir(choice), _DONE), "w").close()
                ok = True
            except Exception as e:
                self.error = str(e) or type(e).__name__
            finally:
                self.downloading = None
            on_done(ok)

        self._thread = threading.Thread(target=work, daemon=True)
        self._thread.start()

    def remove(self, choice):
        if MODELS[choice][2] and not self.downloading:
            shutil.rmtree(self._dir(choice), ignore_errors=True)
