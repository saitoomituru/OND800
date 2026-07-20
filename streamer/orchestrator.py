"""
OND800 NDI Orchestrator

Watches for UVC cameras via udev hotplug, selects the best format per
OND800 streaming policy, and manages a GstNDIStream per camera.

Cameras that disconnect are stopped; cameras that reconnect are restarted.
A single HyperPixelCompositor handles multi-camera display layout:
  1 cam  → fullscreen (90° rotation)
  2-3    → vertical stack (90° rotation, 480 × 800/N each)
  4      → 2×2 grid (no rotation, 240 × 400 each)
"""

import logging
import threading
import time

import pyudev

from .camera import Camera, discover_cameras
from .display import HyperPixelCompositor, display_available
from .gst_stream import GstNDIStream
from .ndi_send import initialize as ndi_initialize

logger = logging.getLogger(__name__)


def _ndi_name(camera: Camera) -> str:
    import re
    base = re.sub(r"[^A-Za-z0-9_-]", "-", camera.name)
    base = re.sub(r"-{2,}", "-", base).strip("-")
    dev_suffix = camera.device.replace("/dev/video", "v")
    return f"OND800-{base}-{dev_suffix}"


class Orchestrator:
    def __init__(self):
        ndi_initialize()
        self._streams: dict[str, GstNDIStream] = {}  # device → stream
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._compositor: HyperPixelCompositor | None = None
        if display_available():
            self._compositor = HyperPixelCompositor()
            logger.info("HyperPixel display detected — compositor mode enabled")
        else:
            logger.info("No display detected — NDI-only mode")

    # ------------------------------------------------------------------
    # Slot assignment and compositor rebuild
    # ------------------------------------------------------------------

    def _rebuild_compositor(self) -> None:
        if self._compositor is None:
            return
        # Assign slots by sorted device path for stable ordering
        with self._lock:
            devices = sorted(self._streams.keys())
            for i, dev in enumerate(devices):
                self._streams[dev].slot = i
        n = len(devices)
        logger.info("Compositor rebuild: %d camera(s), slots=%s", n, devices)
        self._compositor.rebuild(n)

    # ------------------------------------------------------------------
    # Camera lifecycle
    # ------------------------------------------------------------------

    def _start_camera(self, camera: Camera) -> None:
        fmt = camera.best_format()
        if fmt is None:
            logger.warning("No usable format found for %s", camera.device)
            return

        name = _ndi_name(camera)
        # Slot will be corrected by _rebuild_compositor immediately after
        slot = 0
        logger.info("Starting NDI stream: %s  [%s]", name, fmt)
        sp = GstNDIStream(camera, fmt, name,
                          compositor=self._compositor, slot=slot)
        sp.start()
        with self._lock:
            self._streams[camera.device] = sp
        self._rebuild_compositor()

    def _stop_camera(self, device: str) -> None:
        with self._lock:
            sp = self._streams.pop(device, None)
        if sp:
            logger.info("Stopping NDI stream for %s", device)
            sp.stop()
        self._rebuild_compositor()

    # ------------------------------------------------------------------
    # udev hotplug
    # ------------------------------------------------------------------

    def _dispatch_udev_event(self, device: pyudev.Device) -> None:
        """Adapt pyudev's single-device callback to the internal handler."""
        action = device.action
        if action is None:
            logger.warning("udev event without action ignored: %s", device.device_node)
            return
        self._on_udev_event(action, device)

    def _on_udev_event(self, action: str, device: pyudev.Device) -> None:
        dev_node = device.device_node
        if not dev_node or not dev_node.startswith("/dev/video"):
            return
        try:
            num = int(dev_node.replace("/dev/video", ""))
        except ValueError:
            return
        if num >= 10:  # skip Pi5 ISP internal devices
            return

        if action == "add":
            logger.info("Camera added: %s", dev_node)
            time.sleep(0.5)  # let device settle
            camera = Camera(
                device=dev_node,
                name=device.get("ID_MODEL", "Unknown-Camera"),
                bus_id=device.get("ID_PATH", ""),
            )
            self._start_camera(camera)

        elif action == "remove":
            logger.info("Camera removed: %s", dev_node)
            self._stop_camera(dev_node)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        for camera in discover_cameras():
            logger.info("Found camera at startup: %s (%s)", camera.device, camera.name)
            self._start_camera(camera)

        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="video4linux")
        observer = pyudev.MonitorObserver(monitor, callback=self._dispatch_udev_event)
        observer.start()
        logger.info("Hotplug monitor active. Ctrl-C to stop.")

        try:
            self._stop_event.wait()
        finally:
            observer.stop()
            with self._lock:
                devices = list(self._streams.keys())
            for dev in devices:
                self._stop_camera(dev)
            if self._compositor:
                self._compositor.stop()
            logger.info("Orchestrator stopped.")

    def stop(self) -> None:
        self._stop_event.set()
