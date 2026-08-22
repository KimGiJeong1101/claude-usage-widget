"""Downloads the latest Windows build and swaps it in for the running
.exe, then launches the new copy -- the "실제 업데이트" step referenced in
claude-usage-widget-plan.md section 13.3 (stage 2). Stage 1
(usage_widget.update_check) only checks and notifies; this is what
actually happens when the user clicks "지금 업데이트".

Windows-only for now (see can_self_update()): the swap relies on a
Windows-specific quirk -- renaming a currently *running* .exe is allowed
(the OS opens process images with share-delete/share-read semantics),
even though deleting or overwriting it in place is not. That lets this
free up the original path without the process having to exit first:

    1. rename the running exe out of the way (X.exe -> X.exe.old)
    2. write the newly downloaded bytes to the now-vacant X.exe
    3. spawn X.exe (the new version) as an independent process
    4. the caller then shuts this (old) process down normally

macOS's .app bundle is a directory, not a single file, so this approach
doesn't carry over -- that's unbuilt for now.

Known gap: this doesn't know whether the running exe is a portable copy
or one installed via the WiX MSI. Replacing an MSI-tracked file outside
of Windows Installer means a future "repair" could revert it back to the
originally-installed version. Not solved here -- see the plan doc.
"""

import io
import subprocess
import sys
import zipfile
from pathlib import Path

import httpx

_ZIP_URL = "https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-win.zip"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def can_self_update() -> bool:
    return is_frozen() and sys.platform == "win32"


def _current_exe_path() -> Path:
    return Path(sys.executable).resolve()


def _old_path_for(exe: Path) -> Path:
    return exe.with_name(exe.name + ".old")


def cleanup_stale_update_files() -> None:
    """Removes a leftover .old file from a previous update. The process
    that held it open has to have exited before this can succeed, which
    is true by the time the *next* launch of this app runs this -- so
    call it once at startup. Best-effort: a transient failure here just
    leaves the leftover for next time, it doesn't block anything."""
    if not is_frozen():
        return
    try:
        _old_path_for(_current_exe_path()).unlink(missing_ok=True)
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
    """Downloads the latest Windows build and swaps it in for the running
    exe, then launches it. Raises on any failure -- the caller is
    expected to surface that to the user rather than fail silently, since
    they clicked a button expecting something to happen. Returns
    normally after the new process is spawned; the caller is responsible
    for shutting this (old) process down -- this function never does
    that itself, so a caller that ignores the return value doesn't end
    up with two copies fighting over the tray icon."""
    if not can_self_update():
        raise RuntimeError("이 빌드/플랫폼에서는 자동 업데이트를 지원하지 않음")

    new_exe_bytes = _download_new_exe()

    current = _current_exe_path()
    old = _old_path_for(current)
    old.unlink(missing_ok=True)  # leftover from an earlier interrupted update

    current.rename(old)
    try:
        current.write_bytes(new_exe_bytes)
    except Exception:
        old.rename(current)  # restore -- don't leave the app with no exe at all
        raise

    subprocess.Popen([str(current)], close_fds=True)
