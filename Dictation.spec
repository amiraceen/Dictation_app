# -*- mode: python ; coding: utf-8 -*-
# Build: venv/bin/pyinstaller --noconfirm Dictation.spec
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = [], [], ['sounddevice', 'pynput', 'rumps', 'numpy']
for pkg in ('faster_whisper', 'ctranslate2', 'tokenizers', '_sounddevice_data', 'pynput', 'mlx', 'tiktoken'):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

# Bundle the Whisper "small" model so the app works offline with no download.
import glob, os
_snaps = glob.glob(os.path.expanduser("~/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/*/"))
assert _snaps, "Run the app once from source (bash run.sh) to download the Whisper small model first."
MODEL_DIR = _snaps[0]
datas += [(MODEL_DIR + f, 'model') for f in ('config.json', 'model.bin', 'tokenizer.json', 'vocabulary.txt')]

datas += [('menubar/' + f, 'menubar') for f in ('idle.png', 'busy.png', 'recording.png')]

datas += [('web/index.html', 'web'), ('web/fonts', 'web/fonts'), ('web/img', 'web/img')]
datas += collect_data_files('mlx_whisper')          # tokenizer vocabularies, mel filters
hiddenimports += ['ui', 'WebKit', 'PyObjCTools.AppHelper', 'ApplicationServices',
                  'macos', 'meetings', 'notes', 'notetaker', 'settings', 'system', 'speed', 'arabic', 'voicetest', 'models', 'mlx_engine',
                  'mlx_whisper', 'mlx_whisper.transcribe', 'mlx_whisper.audio', 'mlx_whisper.decoding',
                  'mlx_whisper.load_models', 'mlx_whisper.tokenizer', 'mlx_whisper.whisper', 'huggingface_hub', 'certifi',
                  'EventKit', 'ScreenCaptureKit', 'CoreMedia', 'dispatch']

# Word timestamps (numba, SciPy) and model conversion (PyTorch) aren't used: keep them out.
a = Analysis(['dictation.py'], datas=datas, binaries=binaries, hiddenimports=hiddenimports, noarchive=False,
             excludes=['torch', 'numba', 'llvmlite', 'scipy', 'mlx_whisper.torch_whisper', 'mlx_whisper.cli'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Kalam', console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='Kalam')
app = BUNDLE(
    coll,
    name='Kalam.app',
    icon='AppIcon.icns',
    bundle_identifier='com.amira.kalam',
    codesign_identity=None,
    info_plist={
        'CFBundleShortVersionString': '1.0',
        'CFBundleName': 'Kalam',
        'CFBundleDisplayName': 'Kalam',
        'LSUIElement': True,   # menu-bar only; Settings → Show app in Dock adds the icon at runtime
        'NSMicrophoneUsageDescription': 'Kalam records your voice while you hold Right Option, and meetings when you start the Notetaker.',
        'NSCalendarsUsageDescription': 'Kalam shows your next meeting and reminds you to take notes before it starts.',
        'NSCalendarsFullAccessUsageDescription': 'Kalam shows your next meeting and reminds you to take notes before it starts.',
        'NSAppleEventsUsageDescription': 'Kalam pauses Music or Spotify while you dictate, and can mute your sound.',
        'NSHighResolutionCapable': True,
    },
)
