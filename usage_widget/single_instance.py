"""Keeps a second launch of the app from starting a fully independent
second instance -- without this, running the exe twice (double-clicking it
again out of habit, autostart racing a manual launch, etc.) produced two
unrelated background processes, each with its own tray icon (multiple
icons cluttering the tray) and each doing its own PyInstaller onefile
temp-directory extraction/cleanup (surfaced as "Failed to remove temporary
directory" warnings when they stepped on each other, especially around a
self-update relaunch).
"""

import socket
from typing import Optional

# Arbitrary fixed port in the private/dynamic range, chosen only to be
# unlikely to collide with anything else running locally -- its number
# has no other significance.
_LOCK_PORT = 48273

_lock_socket: Optional[socket.socket] = None


def acquire() -> bool:
    """Binding a local TCP port works as a cross-platform mutex without
    any OS-specific API (a Windows named mutex, a Unix PID file with its
    own stale-lock handling, etc.) -- the OS releases the port
    automatically when this process exits or crashes, so there's nothing
    to clean up on the next run either way. Returns False if another
    instance already holds it."""
    global _lock_socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", _LOCK_PORT))
    except OSError:
        sock.close()
        return False
    # Keeping the bound socket alive (never closed) for the process's
    # whole lifetime *is* the lock -- assigning it to a module global
    # here is what stops garbage collection from closing it early.
    _lock_socket = sock
    return True
