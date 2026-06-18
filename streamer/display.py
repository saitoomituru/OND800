"""
Viewfinder display management for OND800.

Detects the HyperPixel 4.0 (800x480) via DRM and renders a scaled camera
feed using GStreamer.

Single-camera: direct tee branch to fbdevsink (legacy path, not used when
compositor is active).

Multi-camera: HyperPixelCompositor owns one GStreamer pipeline with a
compositor element. Each GstNDIStream pushes decoded I420 frames into the
compositor via appsrc. The compositor handles layout and writes to fbdevsink.

Layout rules (fb0 = portrait 480w × 800h):
  1 camera  → fullscreen, 90° CW rotation
  2-3 cams  → 90° CW rotation, each slot 480 × (800 / N), stacked vertically
  4 cams    → no rotation, 2×2 grid, each slot 240 × 400
"""

import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gst, GLib

logger = logging.getLogger(__name__)

# Framebuffer dimensions (portrait mounted HyperPixel 4.0)
HYPERPIXEL_FB_WIDTH  = 480
HYPERPIXEL_FB_HEIGHT = 800
HYPERPIXEL_FPS       = 30

_HYPERPIXEL_CONNECTOR_HINTS = ("DPI", "dpi", "hyperpixel")

# Camera source format expected by compositor appsrc
_SRC_W   = 1920
_SRC_H   = 1080
_SRC_FPS = 30
_SRC_CAPS = (
    f"video/x-raw,format=I420,"
    f"width={_SRC_W},height={_SRC_H},framerate={_SRC_FPS}/1"
)


def find_hyperpixel_connector() -> Optional[tuple[str, int]]:
    import glob, re
    for card in sorted(glob.glob("/dev/dri/card*")):
        try:
            out = subprocess.check_output(
                ["modetest", "-M", card.split("/")[-1], "-c"],
                stderr=subprocess.DEVNULL, text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        for line in out.splitlines():
            if any(h in line for h in _HYPERPIXEL_CONNECTOR_HINTS):
                m = re.compile(r"(\d+)\s+(?:connected|DPI)").search(line)
                if m:
                    return (card, int(m.group(1)))
    return None


def display_available() -> bool:
    if Path("/dev/fb0").exists():
        return True
    return find_hyperpixel_connector() is not None


def _best_sink() -> str:
    for s in ["fbdevsink", "kmssink", "autovideosink"]:
        if Gst.ElementFactory.find(s):
            return s
    return "autovideosink"


def _sink_props(sink: str) -> str:
    if sink == "fbdevsink":
        return " device=/dev/fb0"
    if sink == "kmssink":
        return " force-modesetting=true"
    return ""


# ---------------------------------------------------------------------------
# HyperPixelCompositor
# ---------------------------------------------------------------------------

class HyperPixelCompositor:
    """
    Single GStreamer compositor pipeline for the HyperPixel display.

    Each camera is assigned a slot (0-based). GstNDIStream calls push_frame()
    with the slot index and raw I420 frame bytes. The compositor lays out all
    slots according to the current camera count and writes to fbdevsink.

    Thread-safe: push_frame() can be called from any thread at 30 fps.
    rebuild() is called from the orchestrator when camera count changes.
    """

    def __init__(self) -> None:
        self._pipeline: Optional[Gst.Pipeline] = None
        self._appsrcs: list[Optional[Gst.Element]] = [None] * 4
        self._n_slots: int = 0
        self._loop: Optional[GLib.MainLoop] = None
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rebuild(self, n_cameras: int) -> None:
        """Tear down old pipeline and start a new one for n_cameras."""
        self._stop_pipeline()
        self._n_slots = n_cameras
        if n_cameras > 0:
            self._start_pipeline(n_cameras)

    def push_frame(self, slot: int, data: bytes) -> None:
        """Push a raw I420 frame for the given slot (non-blocking, drops if full)."""
        if slot >= 4:
            return
        appsrc = self._appsrcs[slot]  # atomic read (CPython GIL)
        if appsrc is None:
            return
        buf = Gst.Buffer.new_wrapped(data)
        appsrc.emit("push-buffer", buf)

    def stop(self) -> None:
        self._stop_pipeline()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    @staticmethod
    def _slot_layout(n: int) -> list[tuple[int, int, int, int]]:
        """Return (x, y, w, h) per slot for n cameras."""
        W, H = HYPERPIXEL_FB_WIDTH, HYPERPIXEL_FB_HEIGHT  # 480, 800
        if n == 1:
            return [(0, 0, W, H)]
        if n in (2, 3):
            # Map source long side (1920) to monitor short side (W=480): scale=0.25
            # Source short side: 1080 * 0.25 = 270 → slot height
            # Cap at H//n to prevent overflow when n=3 (3*270=810 > 800)
            slot_h = min(270, H // n)
            return [(0, i * slot_h, W, slot_h) for i in range(n)]
        # 4: 2×2 grid, no rotation
        hw, hh = W // 2, H // 2
        return [
            (0,  0,  hw, hh), (hw, 0,  hw, hh),
            (0,  hh, hw, H - hh), (hw, hh, hw, H - hh),
        ]

    @staticmethod
    def _rotation(n: int) -> str:
        """Clockwise rotation for 1-cam fullscreen only. 2-3 cam: no rotation (landscape strips)."""
        return "videoflip method=clockwise ! " if n == 1 else ""

    # ------------------------------------------------------------------
    # Pipeline build
    # ------------------------------------------------------------------

    def _build_pipeline_str(self, n: int) -> str:
        slots = self._slot_layout(n)
        rot   = self._rotation(n)
        sink  = _best_sink()
        sprops = _sink_props(sink)

        # Compositor pad position properties (width/height set by videoscale upstream)
        pad_pos = " ".join(
            f"sink_{i}::xpos={x} sink_{i}::ypos={y}"
            for i, (x, y, w, h) in enumerate(slots)
        )
        comp_out_caps = (
            f"video/x-raw,format=BGRx,"
            f"width={HYPERPIXEL_FB_WIDTH},height={HYPERPIXEL_FB_HEIGHT},"
            f"framerate={HYPERPIXEL_FPS}/1"
        )
        comp_line = (
            f"compositor name=comp background=black {pad_pos} "
            f"! {comp_out_caps} "
            f"! {sink}{sprops}"
        )

        src_branches = []
        for i, (x, y, w, h) in enumerate(slots):
            branch = (
                f"appsrc name=src_{i} format=time is-live=true do-timestamp=true "
                f"caps=\"{_SRC_CAPS}\" "
                f"! queue leaky=downstream max-size-buffers=2 "
                f"! videoconvert ! {rot}videoscale "
                f"! video/x-raw,width={w},height={h} ! comp.sink_{i}"
            )
            src_branches.append(branch)

        return "  ".join(src_branches) + "  " + comp_line

    # ------------------------------------------------------------------
    # Pipeline lifecycle
    # ------------------------------------------------------------------

    def _start_pipeline(self, n: int) -> None:
        pipeline_str = self._build_pipeline_str(n)
        logger.debug("Compositor pipeline (%d cam): %s", n, pipeline_str)
        try:
            self._pipeline = Gst.parse_launch(pipeline_str)
        except GLib.GError as exc:
            logger.error("Compositor pipeline parse failed: %s", exc)
            self._pipeline = None
            return

        for i in range(n):
            self._appsrcs[i] = self._pipeline.get_by_name(f"src_{i}")

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

        self._loop = GLib.MainLoop()
        self._pipeline.set_state(Gst.State.PLAYING)
        logger.info("HyperPixel compositor started (%d cameras, layout=%s)",
                    n, self._slot_layout(n))

        self._thread = threading.Thread(
            target=self._loop.run, daemon=True, name="gst-compositor"
        )
        self._thread.start()

    def _stop_pipeline(self) -> None:
        # Zero out appsrcs first so push_frame drops frames during teardown
        self._appsrcs = [None] * 4
        if self._loop and self._loop.is_running():
            self._loop.quit()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
        logger.debug("HyperPixel compositor stopped")

    def _on_message(self, bus, message) -> None:
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, dbg = message.parse_error()
            logger.error("Compositor GStreamer error: %s (%s)", err, dbg)
        elif t == Gst.MessageType.EOS:
            logger.warning("Compositor EOS received")


# ---------------------------------------------------------------------------
# Legacy single-stream display branch (kept for reference / fallback)
# ---------------------------------------------------------------------------

class ViewfinderDisplay:
    """Legacy: single-camera display branch spliced into a tee pipeline."""

    def build_display_branch(self) -> str:
        sink   = _best_sink()
        sprops = _sink_props(sink)
        if sink == "fbdevsink":
            return (
                f"queue leaky=downstream ! "
                f"videoconvert ! videoscale ! "
                f"videoflip method=clockwise ! "
                f"video/x-raw,format=BGRx,"
                f"width={HYPERPIXEL_FB_WIDTH},height={HYPERPIXEL_FB_HEIGHT} ! "
                f"{sink}{sprops}"
            )
        fmt_caps = (
            f"video/x-raw,width={HYPERPIXEL_FB_WIDTH},height={HYPERPIXEL_FB_HEIGHT},"
            f"framerate={HYPERPIXEL_FPS}/1"
        )
        return (
            f"queue leaky=downstream ! videoscale ! videoconvert ! "
            f"{fmt_caps} ! {sink}{sprops}"
        )
