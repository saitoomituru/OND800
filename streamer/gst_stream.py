"""
GStreamer-based NDI sender + viewfinder for OND800.

Pipeline (NDI only):
  v4l2src (MJPG) → jpegdec → videoconvert → UYVY → appsink → NDI SDK

Pipeline (NDI + HyperPixel viewfinder):
  v4l2src (MJPG) → jpegdec → tee
    ├─ queue → videoconvert → videoscale → 800x480 → kmssink   (viewfinder)
    └─ queue → videoconvert → UYVY → appsink → NDI SDK         (NDI out)
"""

import logging
import threading
from typing import Optional

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gst, GLib

from .camera import Camera, Format
from .display import ViewfinderDisplay, display_available
from .ndi_send import NDISender

logger = logging.getLogger(__name__)

Gst.init(None)


class GstNDIStream:
    """
    Captures from a UVC camera via GStreamer and sends frames over NDI.
    If a HyperPixel display is detected, also renders a 800x480 viewfinder.
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
        self._has_display = display_available()

    def _src_caps(self) -> str:
        w, h, fps = self.fmt.width, self.fmt.height, int(self.fmt.fps)
        if self.fmt.pixelformat == "MJPG":
            return f"image/jpeg,width={w},height={h},framerate={fps}/1"
        return f"video/x-raw,format=YUY2,width={w},height={h},framerate={fps}/1"

    def _decode_element(self) -> str:
        if self.fmt.pixelformat == "MJPG":
            return "jpegdec ! "
        return ""  # YUYV needs no decode, just conversion

    def _build_pipeline_str(self) -> str:
        dev = self.camera.device
        src = f"v4l2src device={dev} ! {self._src_caps()} ! {self._decode_element()}"

        ndi_branch = (
            "queue leaky=downstream ! "
            f"videoconvert ! video/x-raw,format=UYVY ! "
            "appsink name=sink emit-signals=true max-buffers=2 drop=true sync=false"
        )

        if self._has_display:
            vf = ViewfinderDisplay()
            display_branch = vf.build_display_branch()
            # Explicitly convert to I420 before tee so both branches
            # can independently re-convert to their required format.
            pipeline = (
                f"{src}"
                f"videoconvert ! video/x-raw,format=I420 ! "
                f"tee name=t "
                f"t. ! {ndi_branch} "
                f"t. ! {display_branch}"
            )
            logger.info("[%s] viewfinder enabled (HyperPixel detected)", self.ndi_name)
        else:
            pipeline = (
                f"{src}"
                f"videoconvert ! video/x-raw,format=UYVY ! "
                f"appsink name=sink emit-signals=true max-buffers=2 drop=true sync=false"
            )
            logger.info("[%s] no display detected — NDI only", self.ndi_name)

        return pipeline

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

        self._sender = NDISender(self.ndi_name, clock_video=True,
                                 width=self.fmt.width, height=self.fmt.height)
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
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"gst-{self.ndi_name}"
        )
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
