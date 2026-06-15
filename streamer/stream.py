"""NDI stream process management for OND800."""

import logging
import os
import subprocess
import threading
import time
from pathlib import Path

from .camera import Camera, Format

logger = logging.getLogger(__name__)

# v4l2ndi binary location (relative to this file's package root)
_REPO_ROOT = Path(__file__).resolve().parent.parent
V4L2NDI_BIN = _REPO_ROOT.parent / "V4L2-to-NDI" / "build" / "v4l2ndi"
V4L2NDI_LIB = _REPO_ROOT.parent / "V4L2-to-NDI" / "lib"

RESTART_DELAY = 3.0   # seconds before restarting a crashed stream
MAX_RESTARTS = 10     # give up after this many consecutive crashes


def _fps_to_ndi_args(fps: float) -> tuple[str, str]:
    """Convert float fps to v4l2ndi -n/-e integer pair."""
    # v4l2ndi uses numerator/denominator; keep integers small
    if fps == 60:
        return ("60000", "1000001")
    if fps == 30:
        return ("30000", "1000001")
    if fps == 24:
        return ("24000", "1000001")
    # generic: scale to avoid float precision issues
    n = int(fps * 1000)
    return (str(n), "1000001")


class StreamProcess:
    """Manages a single v4l2ndi process for one camera."""

    def __init__(self, camera: Camera, fmt: Format, ndi_name: str):
        self.camera = camera
        self.fmt = fmt
        self.ndi_name = ndi_name
        self._proc: subprocess.Popen | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._restarts = 0

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        if self._thread:
            self._thread.join(timeout=10)

    def _build_cmd(self) -> list[str]:
        n, e = _fps_to_ndi_args(self.fmt.fps)
        cmd = [
            str(V4L2NDI_BIN),
            "-d", self.camera.device,
            "-x", str(self.fmt.width),
            "-y", str(self.fmt.height),
            "-n", n,
            "-e", e,
            "-v", self.ndi_name,
            "-i",  # threaded
        ]
        if self.fmt.pixelformat == "UYVY":
            cmd.append("-u")
        elif self.fmt.pixelformat == "NV12":
            cmd.append("-m")
        # MJPG: v4l2ndi will fall back to YUYV — acceptable for now
        return cmd

    def _run_loop(self):
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = str(V4L2NDI_LIB)

        while not self._stop_event.is_set():
            if self._restarts >= MAX_RESTARTS:
                logger.error("[%s] exceeded max restarts (%d), giving up",
                             self.ndi_name, MAX_RESTARTS)
                break

            cmd = self._build_cmd()
            logger.info("[%s] starting: %s", self.ndi_name, " ".join(cmd))
            try:
                self._proc = subprocess.Popen(
                    cmd, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True,
                )
                for line in self._proc.stdout:
                    line = line.rstrip()
                    if line:
                        logger.debug("[%s] %s", self.ndi_name, line)
                self._proc.wait()
            except Exception as exc:
                logger.error("[%s] launch error: %s", self.ndi_name, exc)

            if self._stop_event.is_set():
                break

            rc = self._proc.returncode if self._proc else -1
            self._restarts += 1
            logger.warning("[%s] exited (rc=%d), restart %d/%d in %.1fs",
                           self.ndi_name, rc, self._restarts, MAX_RESTARTS,
                           RESTART_DELAY)
            self._stop_event.wait(RESTART_DELAY)

    def reset_restart_count(self):
        self._restarts = 0
