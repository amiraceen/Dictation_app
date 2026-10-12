# -*- mode: python ; coding: utf-8 -*-
# Build: venv/bin/pyinstaller --noconfirm Dictation.spec
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], ['sounddevice', 'pynput', 'rumps', 'numpy']
for pkg in ('faster_whisper', 'ctranslate2', 'tokenizers', '_sounddevice_data', 'pynput'):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

# Bundle the Whisper "small" model so the app works offline with no download.
import glob, os
_snaps = glob.glob(os.path.expanduser("~/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/*/"))
assert _snaps, "Run the app once from source (bash run.sh) to download the Whisper small model first."
MODEL_DIR = _snaps[0]
datas += [(MODEL_DIR + f, 'model') for f in ('config.json', 'model.bin', 'tokenizer.json', 'vocabulary.txt')]

datas += [('menubar/' + f, 'menubar') for f in ('idle.png', 'busy.png', 'recording.png')]

datas += [('web/index.html', 'web')]
hiddenimports += ['ui', 'WebKit', 'PyObjCTools.AppHelper', 'ApplicationServices',
                  'macos', 'meetings', 'notes', 'notetaker', 'settings', 'system', 'speed', 'arabic', 'voicetest',
                  'EventKit', 'ScreenCaptureKit', 'CoreMedia', 'dispatch']

a = Analysis(['dictation.py'], datas=datas, binaries=binaries, hiddenimports=hiddenimports, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Dictation', console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='Dictation')
app = BUNDLE(
    coll,
    name='Dictation 2.app',
    icon='AppIcon.icns',
    bundle_identifier='com.amira.dictation2',
    codesign_identity=None,
    info_plist={
        'CFBundleShortVersionString': '1.0',
        'CFBundleName': 'Dictation 2',
        'CFBundleDisplayName': 'Dictation 2',
        'LSUIElement': True,   # menu-bar only; Settings → Show app in Dock adds the icon at runtime
        'NSMicrophoneUsageDescription': 'Dictation records your voice while you hold Right Option, and meetings when you start the Notetaker.',
        'NSCalendarsUsageDescription': 'Dictation shows your next meeting and reminds you to take notes before it starts.',
        'NSCalendarsFullAccessUsageDescription': 'Dictation shows your next meeting and reminds you to take notes before it starts.',
        'NSAppleEventsUsageDescription': 'Dictation pauses Music or Spotify while you dictate, and can mute your sound.',
        'NSHighResolutionCapable': True,
    },
)
