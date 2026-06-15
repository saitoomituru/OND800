"""
GStreamer-based NDI sender for OND800.

Pipeline: v4l2src (MJPG) → jpegdec → videoconvert → UYVY → appsink → NDI SDK

This replaces the v4l2ndi binary for cameras where MJPG is available,
enabling 1920x1080@30fps NDI output over standard NDI (UYVY on the wire).
"""

import logging
import threading
import time
from typing import Optional

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gst, GLib

from .camera import Camera, Format
from .ndi_send import NDISender, initialize as ndi_initialize

logger = logging.getLogger(__name__)

Gst.init(None)


class GstNDIStream:
    """
    Captures from a UVC camera via GStreamer and sends frames over NDI.
    Supports MJPG (decoded to UYVY) and YUYV (converted to UYVY).
    """

    def __init__(self, camera: Camera, fmt: Format, ndi_name: str):
        self.camera = camera
        self.fmt = fmt
        self.ndi_name = ndi_name

        self._pipeline: Optional[Gst.Pipeline] = None
        self._sender: Optional[NDISender] = None
        self._loop: Optional[GLib.MainLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._frame_count = 0
        self._drop_count = 0

    def _build_pipeline_str(self) -> str:
        w, h = self.fmt.width, self.fmt.height
        fps = int(self.fmt.fps)
        dev = self.camera.device

        if self.fmt.pixelformat == "MJPG":
            return (
                f"v4l2src device={dev} ! "
                f"image/jpeg,width={w},height={h},framerate={fps}/1 ! "
                f"jpegdec ! "
                f"videoconvert ! "
                f"video/x-raw,format=UYVY,width={w},height={h} ! "
                f"appsink name=sink emit-signals=true max-buffers=2 drop=true sync=false"
            )
        else:
            # YUYV → UYVY conversion
            return (
                f"v4l2src device={dev} ! "
                f"video/x-raw,format=YUY2,width={w},height={h},framerate={fps}/1 ! "
                f"videoconvert ! "
                f"video/x-raw,format=UYVY,width={w},height={h} ! "
                f"appsink name=sink emit-signals=true max-buffers=2 drop=true sync=false"
            )

    def _on_new_sample(self, appsink):
        sample = appsink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.OK

        buf = sample.get_buffer()
        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            return Gst.FlowReturn.OK

        try:
            if self._sender:
                fps_n = int(self.fmt.fps * 1000)
                self._sender.send_uyvy(
                    bytes(mapinfo.data),
                    self.fmt.width,
                    self.fmt.height,
                    fps_n=fps_n,
                    fps_d=1000,
                )
                self._frame_count += 1
                if self._frame_count % (int(self.fmt.fps) * 10) == 0:
                    logger.info("[%s] frames=%d drops=%d connections=%d",
                                self.ndi_name, self._frame_count,
                                self._drop_count, self._sender.connections)
        finally:
            buf.unmap(mapinfo)

        return Gst.FlowReturn.OK

    def _on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            logger.warning("[%s] GStreamer EOS", self.ndi_name)
            self._loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error("[%s] GStreamer error: %s (%s)", self.ndi_name, err, debug)
            self._loop.quit()

    def _run(self):
        pipeline_str = self._build_pipeline_str()
        logger.info("[%s] pipeline: %s", self.ndi_name, pipeline_str)

        self._pipeline = Gst.parse_launch(pipeline_str)
        appsink = self._pipeline.get_by_name("sink")
        appsink.connect("new-sample", self._on_new_sample)

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

        self._sender = NDISender(self.ndi_name, clock_video=True)
        self._loop = GLib.MainLoop()

        self._pipeline.set_state(Gst.State.PLAYING)
        logger.info("[%s] NDI stream started [%s]", self.ndi_name, self.fmt)

        try:
            self._loop.run()
        finally:
            self._pipeline.set_state(Gst.State.NULL)
            self._sender.destroy()
            logger.info("[%s] stopped (frames=%d drops=%d)",
                        self.ndi_name, self._frame_count, self._drop_count)

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"gst-{self.ndi_name}")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._loop and self._loop.is_running():
            self._loop.quit()
        if self._thread:
            self._thread.join(timeout=10)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
