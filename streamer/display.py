"""
Viewfinder display management for OND800.

Detects the HyperPixel 4.0 (800x480) via DRM and renders a scaled camera
feed using GStreamer kmssink. Runs as a separate thread alongside NDI output.
"""

import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gst, GLib

logger = logging.getLogger(__name__)

HYPERPIXEL_WIDTH  = 800
HYPERPIXEL_HEIGHT = 480
HYPERPIXEL_FPS    = 60

# DRM connector names Pimoroni HyperPixel 4.0 shows up as on Pi5
_HYPERPIXEL_CONNECTOR_HINTS = ("DPI", "dpi", "hyperpixel")


def find_hyperpixel_connector() -> Optional[tuple[str, int]]:
    """
    Scan DRM cards for a connector that looks like HyperPixel (DPI type).
    Returns (card_path, connector_id) or None.
    """
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
                m = re.search(r"(\d+)\s+(?:connected|DPI)", line)
                if m:
                    return (card, int(m.group(1)))
    return None


def display_available() -> bool:
    """True if a HyperPixel-like DRM connector is detected."""
    # Fast check: look for DPI/framebuffer device
    if Path("/dev/fb0").exists():
        return True
    result = find_hyperpixel_connector()
    return result is not None


class ViewfinderDisplay:
    """
    Renders a scaled (800x480) viewfinder onto the HyperPixel 4.0 display.
    Receives frames via GStreamer appsrc fed from the main capture pipeline's tee.
    """

    # GStreamer display sink preference order for Pi5/HyperPixel
    _SINK_CANDIDATES = [
        "kmssink",       # DRM/KMS — best for HyperPixel DPI, no desktop needed
        "fbdevsink",     # raw framebuffer fallback
        "waylandsink",   # if Wayland compositor is running
        "autovideosink", # last resort (may open a window on HDMI)
    ]

    def __init__(self):
        self._loop: Optional[GLib.MainLoop] = None
        self._thread: Optional[threading.Thread] = None

    def _best_sink(self) -> str:
        for sink in self._SINK_CANDIDATES:
            el = Gst.ElementFactory.find(sink)
            if el:
                logger.debug("Display sink: %s", sink)
                return sink
        return "autovideosink"

    def build_display_branch(self) -> str:
        """
        Return the GStreamer bin description for the display branch.
        Intended to be spliced into a `tee` pipeline.

            tee name=t
              t. ! queue ! [display branch]
              t. ! queue ! [NDI branch]
        """
        sink = self._best_sink()
        sink_props = ""
        if sink == "kmssink":
            # connector-id auto-detected; force-modesetting needed for DPI
            sink_props = " force-modesetting=true"
        elif sink == "fbdevsink":
            sink_props = " device=/dev/fb0"

        return (
            f"queue leaky=downstream ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={HYPERPIXEL_WIDTH},height={HYPERPIXEL_HEIGHT},"
            f"framerate={HYPERPIXEL_FPS}/1 ! "
            f"{sink}{sink_props}"
        )
