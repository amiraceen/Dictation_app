"""
Pure helpers for system features: launch at login and pausing media.
No AppKit imports, so it can be tested anywhere; macos.py does the actual
system calls.
"""

import os

# ─── Launch at login ─────────────────────────────────────────────────────────

LOGIN_AGENT_LABEL = "com.amira.kalam.login"


def login_agent_path(home=None):
    home = home or os.path.expanduser("~")
    return os.path.join(home, "Library", "LaunchAgents", LOGIN_AGENT_LABEL + ".plist")


def app_bundle_path(executable):
    """'/Applications/Dictation.app/Contents/MacOS/Dictation' → '/Applications/Dictation.app'."""
    path = os.path.abspath(executable)
    while path and path != os.path.dirname(path):
        if path.endswith(".app"):
            return path
        path = os.path.dirname(path)
    return None


def login_program_args(frozen, executable, script):
    """How the login item starts the app: the bundle via `open`, or the source script."""
    bundle = app_bundle_path(executable) if frozen else None
    if bundle:
        return ["/usr/bin/open", "-a", bundle]
    return [executable, os.path.abspath(script)]


def login_agent_plist(program_args):
    return {"Label": LOGIN_AGENT_LABEL, "ProgramArguments": list(program_args),
            "RunAtLoad": True, "ProcessType": "Interactive"}


# ─── Media ───────────────────────────────────────────────────────────────────

# Apps we can ask to pause. `is running` checks never launch an app that's closed.
MEDIA_APPS = ["Music", "Spotify"]


def pause_media_script():
    """AppleScript that pauses playing players and returns their names, comma-separated."""
    lines = ["set paused to {}"]
    for app in MEDIA_APPS:
        lines += [f'if application "{app}" is running then',
                  f'  tell application "{app}"',
                  '    if player state is playing then',
                  '      pause',
                  f'      set end of paused to "{app}"',
                  '    end if',
                  '  end tell',
                  'end if']
    lines += ["set AppleScript's text item delimiters to \",\"",
              "return paused as text"]
    return "\n".join(lines)


def resume_media_script(apps):
    apps = [a for a in apps if a in MEDIA_APPS]
    return "\n".join(f'if application "{a}" is running then tell application "{a}" to play'
                     for a in apps)


def parse_paused(output):
    return [a for a in (s.strip() for s in output.split(",")) if a in MEDIA_APPS]

