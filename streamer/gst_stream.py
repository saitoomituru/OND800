"""
GStreamer-based NDI sender + viewfinder for OND800.

Pipeline (display via compositor):
  v4l2src (MJPG) → jpegdec → videoconvert → I420 → tee
    ├─ queue → videoconvert → UYVY → appsink → NDI SDK
    └─ queue → appsink(disp) → push to HyperPixelCompositor

Pipeline (NDI only, no display):
  v4l2src (MJPG) → jpegdec → videoconvert → UYVY → appsink → NDI SDK
"""

import logging
import threading
from typing import Optional

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gst, GLib

from .camera import Camera, Format
from .display import HyperPixelCompositor
from .ndi_send import NDISender

logger = logging.getLogger(__name__)

Gst.init(None)


class GstNDIStream:
    """
    Captures from a UVC camera via GStreamer and sends frames over NDI.
    If a HyperPixelCompositor is provided, also pushes decoded frames to
    it for multi-camera display compositing.
    """

    def __init__(
        self,
        camera: Camera,
        fmt: Format,
        ndi_name: str,
        compositor: Optional[HyperPixelCompositor] = None,
        slot: int = 0,
    ):
        self.camera = camera
        self.fmt = fmt
        self.ndi_name = ndi_name
        self.slot = slot  # mutable: orchestrator may update on camera count change

        self._compositor = compositor
        self._pipeline: Optional[Gst.Pipeline] = None
        self._sender: Optional[NDISender] = None
        self._loop: Optional[GLib.MainLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._drop_count = 0

    def _src_caps(self) -> str:
        w, h, fps = self.fmt.width, self.fmt.height, int(self.fmt.fps)
        if self.fmt.pixelformat == "MJPG":
            return f"image/jpeg,width={w},height={h},framerate={fps}/1"
        return f"video/x-raw,format=YUY2,width={w},height={h},framerate={fps}/1"

    def _decode_element(self) -> str:
        return "jpegdec ! " if self.fmt.pixelformat == "MJPG" else ""

    def _build_pipeline_str(self) -> str:
        dev = self.camera.device
        src = f"v4l2src device={dev} ! {self._src_caps()} ! {self._decode_element()}"

        ndi_branch = (
            "queue leaky=downstream ! "
            "videoconvert ! video/x-raw,format=UYVY ! "
            "appsink name=sink emit-signals=true max-buffers=2 drop=true sync=false"
        )

        if self._compositor is not None:
            # Tee: NDI branch + display branch (I420 → compositor)
            disp_branch = (
                "queue leaky=downstream max-size-buffers=2 ! "
                "appsink name=disp emit-signals=true max-buffers=1 drop=true sync=false"
            )
            pipeline = (
                f"{src}"
                f"videoconvert ! video/x-raw,format=I420 ! "
                f"tee name=t "
                f"t. ! {ndi_branch} "
                f"t. ! {disp_branch}"
            )
            logger.info("[%s] compositor display (slot %d)", self.ndi_name, self.slot)
        else:
            # NDI only
            pipeline = (
                f"{src}"
                f"videoconvert ! video/x-raw,format=UYVY ! "
                f"appsink name=sink emit-signals=true max-buffers=2 drop=true sync=false"
            )
            logger.info("[%s] no display — NDI only", self.ndi_name)

        return pipeline

    # ------------------------------------------------------------------
    # GStreamer callbacks
    # ------------------------------------------------------------------

    def _on_ndi_sample(self, appsink):
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
                    logger.info(
                        "[%s] frames=%d drops=%d connections=%d",
                        self.ndi_name, self._frame_count,
                        self._drop_count, self._sender.connections,
                    )
        finally:
            buf.unmap(mapinfo)
        return Gst.FlowReturn.OK

    def _on_disp_sample(self, appsink):
        sample = appsink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.OK
        compositor = self._compositor
        if compositor is None:
            return Gst.FlowReturn.OK

        buf = sample.get_buffer()
        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if ok:
            try:
                compositor.push_frame(self.slot, bytes(mapinfo.data))
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

    # ------------------------------------------------------------------
    # Run / stop
    # ------------------------------------------------------------------

    def _run(self):
        pipeline_str = self._build_pipeline_str()
        logger.info("[%s] pipeline: %s", self.ndi_name, pipeline_str)

        self._pipeline = Gst.parse_launch(pipeline_str)

        ndi_sink = self._pipeline.get_by_name("sink")
        ndi_sink.connect("new-sample", self._on_ndi_sample)

        if self._compositor is not None:
            disp_sink = self._pipeline.get_by_name("disp")
            if disp_sink:
                disp_sink.connect("new-sample", self._on_disp_sample)

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

        self._sender = NDISender(
            self.ndi_name, clock_video=True,
            width=self.fmt.width, height=self.fmt.height,
        )
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
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"gst-{self.ndi_name}"
        )
        self._thread.start()

    def stop(self):
        if self._loop and self._loop.is_running():
            self._loop.quit()
        if self._thread:
            self._thread.join(timeout=10)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
