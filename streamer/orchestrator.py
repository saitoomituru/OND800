"""
OND800 NDI Orchestrator

Watches for UVC cameras via udev hotplug, selects the best format per
OND800 streaming policy, and manages a v4l2ndi process per camera.
Cameras that disconnect are stopped; cameras that reconnect are restarted.
"""

import logging
import signal
import threading
import time

import pyudev

from .camera import Camera, discover_cameras
from .gst_stream import GstNDIStream
from .ndi_send import initialize as ndi_initialize

logger = logging.getLogger(__name__)


def _ndi_name(camera: Camera) -> str:
    """Build a stable NDI stream name from camera info."""
    import re
    base = re.sub(r"[^A-Za-z0-9_-]", "-", camera.name)
    base = re.sub(r"-{2,}", "-", base).strip("-")
    dev_suffix = camera.device.replace("/dev/video", "v")
    return f"OND800-{base}-{dev_suffix}"


class Orchestrator:
    def __init__(self):
        ndi_initialize()
        self._streams: dict[str, GstNDIStream] = {}  # device -> GstNDIStream
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def _start_camera(self, camera: Camera):
        fmt = camera.best_format()
        if fmt is None:
            logger.warning("No usable format found for %s", camera.device)
            return

        name = _ndi_name(camera)
        logger.info("Starting NDI stream: %s  [%s]", name, fmt)
        sp = GstNDIStream(camera, fmt, name)
        sp.start()
        with self._lock:
            self._streams[camera.device] = sp

    def _stop_camera(self, device: str):
        with self._lock:
            sp = self._streams.pop(device, None)
        if sp:
            logger.info("Stopping NDI stream for %s", device)
            sp.stop()

    def _on_udev_event(self, action: str, device: pyudev.Device):
        dev_node = device.device_node
        if not dev_node or not dev_node.startswith("/dev/video"):
            return
        # skip internal Pi5 ISP devices (video10+)
        try:
            num = int(dev_node.replace("/dev/video", ""))
        except ValueError:
            return
        if num >= 10:
            return

        if action == "add":
            logger.info("Camera added: %s", dev_node)
            time.sleep(0.5)  # let the device settle before opening
            camera = Camera(
                device=dev_node,
                name=device.get("ID_MODEL", "Unknown-Camera"),
                bus_id=device.get("ID_PATH", ""),
            )
            self._start_camera(camera)

        elif action == "remove":
            logger.info("Camera removed: %s", dev_node)
            self._stop_camera(dev_node)

    def run(self):
        # start streams for cameras already connected at launch
        for camera in discover_cameras():
            logger.info("Found camera at startup: %s (%s)", camera.device, camera.name)
            self._start_camera(camera)

        # watch for hotplug events
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="video4linux")
        observer = pyudev.MonitorObserver(monitor, callback=self._on_udev_event)
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
            logger.info("Orchestrator stopped.")

    def stop(self):
        self._stop_event.set()
