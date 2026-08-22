"""Downloads the latest Windows build and swaps it in for the running
.exe, then launches the new copy -- the "실제 업데이트" step referenced in
claude-usage-widget-plan.md section 13.3 (stage 2). Stage 1
(usage_widget.update_check) only checks and notifies; this is what
actually happens when the user clicks "지금 업데이트".

Windows-only for now (see can_self_update()).

The swap and relaunch are done by a small detached cmd.exe helper
script, not by this process directly. An earlier version renamed the
running exe out of the way and overwrote it in place while still
running (a currently-running exe can be renamed on Windows even though
it can't be deleted or overwritten), then launched the new copy
directly as a child of this process. That worked for freeing up the
file, but the relaunched copy then failed to start with a PyInstaller
bootloader error: "Security validation failure: parent process has
different executable!" PyInstaller 6.9+ validates, whenever a onefile
exe looks like it was spawned by another instance of itself, that the
parent process's own executable image still genuinely matches what the
parent process actually loaded -- and by the time the child launched,
the parent's on-disk file no longer matched (renamed away from under
it, replaced with different bytes), so the check correctly flagged it
as suspicious.

Routing the relaunch through a plain cmd.exe helper sidesteps that
check entirely, since "spawned by another instance of the same
executable" never applies -- the parent of the final relaunched app is
cmd.exe, not this app. It also means the file swap only happens after
this process has fully exited (the helper waits on this process's PID),
so there's no more need for the old rename-while-running trick either:
by the time anything touches the file, nothing still has it open.

macOS's .app bundle is a directory, not a single file, so this approach
doesn't carry over -- that's unbuilt for now.

Known gap: this doesn't know whether the running exe is a portable copy
or one installed via the WiX MSI. Replacing an MSI-tracked file outside
of Windows Installer means a future "repair" could revert it back to the
originally-installed version. Not solved here -- see the plan doc.
"""

import io
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import httpx

_ZIP_URL = "https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-win.zip"

# Waits for the launching process (this app, about to shut itself down) to
# actually exit before touching any files, then swaps the staged download
# into place and starts it. Written with the system's ANSI codepage (see
# apply_update()), not UTF-8 -- cmd.exe reads batch files using the active
# codepage by default, and paths here can contain non-ASCII characters
# (Korean usernames/folder names are common for this app's actual users).
# The 30-iteration cap is a safety net in case this process somehow never
# exits; shutting down normally (icon.stop() + shutdown_gui()) is near
# instant, so this should only ever loop once or twice in practice.
_RELAUNCH_SCRIPT = """@echo off
setlocal
set "PID={pid}"
set "TARGET={target}"
set "STAGED={staged}"
set /a COUNT=0
:waitloop
tasklist /FI "PID eq %PID%" 2>NUL | findstr /C:"%PID%" >nul
if %errorlevel%==0 (
    set /a COUNT+=1
    if %COUNT% GEQ 30 goto proceed
    timeout /t 1 /nobreak >nul
    goto waitloop
)
:proceed
move /Y "%STAGED%" "%TARGET%" >nul
start "" "%TARGET%"
del "%~f0"
"""


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def can_self_update() -> bool:
    return is_frozen() and sys.platform == "win32"


def _current_exe_path() -> Path:
    return Path(sys.executable).resolve()


def _staged_path_for(exe: Path) -> Path:
    """Where the newly-downloaded exe is written before the relaunch
    helper moves it into place -- never the same path as the currently
    running exe, since that file can't be overwritten while it's open."""
    return exe.with_name(f"{exe.stem}.new{exe.suffix}")


def _relaunch_script_path_for(exe: Path) -> Path:
    return exe.with_name("_update_relaunch.bat")


def cleanup_stale_update_files() -> None:
    """Removes leftovers from an update interrupted mid-flight (e.g. the
    app was killed between staging the new copy and the relaunch helper
    actually swapping it in). Best-effort, meant to be called once at
    startup: a transient failure here just leaves the leftover for next
    time, it doesn't block anything.

    Also cleans up `X.exe.old`, the previous (pre-v0.2.3) scheme's
    leftover name -- that version's failure mode left one behind whenever
    the relaunch crashed (see apply_update()'s docstring), and anyone
    who hit that bug before upgrading would otherwise have it linger
    forever, since a build's own code has no way to know about a naming
    scheme introduced after it was compiled."""
    if not is_frozen():
        return
    current = _current_exe_path()
    legacy_old = current.with_name(current.name + ".old")
    for path in (_staged_path_for(current), _relaunch_script_path_for(current), legacy_old):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def _download_new_exe() -> bytes:
    response = httpx.get(_ZIP_URL, timeout=60, follow_redirects=True)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".exe")]
        if not names:
            raise RuntimeError("release zip에 .exe가 없음")
        return zf.read(names[0])


def apply_update() -> None:
    """Downloads the latest Windows build, stages it next to the running
    exe, and hands off to a detached helper that waits for this process
    to exit before swapping it into place and launching it (see the
    module docstring for why a helper is involved). Raises on any failure
    up through the download/staging step -- the caller is expected to
    surface that to the user rather than fail silently, since they
    clicked a button expecting something to happen. Returns normally once
    the helper is spawned; the caller is responsible for shutting this
    process down afterwards, since the helper is waiting on this exact
    PID before it touches anything."""
    if not can_self_update():
        raise RuntimeError("이 빌드/플랫폼에서는 자동 업데이트를 지원하지 않음")

    new_exe_bytes = _download_new_exe()

    current = _current_exe_path()
    staged = _staged_path_for(current)
    staged.write_bytes(new_exe_bytes)

    script_path = _relaunch_script_path_for(current)
    script = _RELAUNCH_SCRIPT.format(pid=os.getpid(), target=current, staged=staged)
    script_path.write_text(script, encoding="mbcs")

    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )
