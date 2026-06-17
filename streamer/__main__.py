"""Entry point: python3 -m streamer"""

import logging
import os
import signal
import sys

from .orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

_PID_FILE = "/run/ond800-streamer.pid"


def _acquire_pid_lock() -> None:
    """Ensure only one instance runs. Exits with error if another is already running."""
    if os.path.exists(_PID_FILE):
        try:
            existing_pid = int(open(_PID_FILE).read().strip())
            # check if that PID is actually alive
            os.kill(existing_pid, 0)
            logger.error(
                "OND800 streamer is already running as PID %d "
                "(detected via %s). "
                "Stop the daemon first: sudo systemctl stop ond800-streamer",
                existing_pid, _PID_FILE,
            )
            sys.exit(1)
        except (ValueError, ProcessLookupError):
            # stale PID file — previous run didn't clean up
            logger.warning("Stale PID file found (%s), removing.", _PID_FILE)
            os.remove(_PID_FILE)

    try:
        with open(_PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except PermissionError:
        # /run may not be writable when launched interactively as non-root.
        # Fall back to /tmp — still provides same-user protection.
        global _PID_FILE
        _PID_FILE = "/tmp/ond800-streamer.pid"
        with open(_PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        logger.warning("Could not write to /run, using %s for PID lock.", _PID_FILE)


def _release_pid_lock() -> None:
    try:
        os.remove(_PID_FILE)
    except FileNotFoundError:
        pass


_acquire_pid_lock()

orc = Orchestrator()


def _handle_signal(sig, frame):
    print("\nShutting down...")
    orc.stop()
    _release_pid_lock()
    sys.exit(0)


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

try:
    orc.run()
finally:
    _release_pid_lock()
