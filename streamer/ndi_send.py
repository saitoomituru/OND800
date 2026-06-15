"""
Thin ctypes wrapper around NDI SDK v6 send API.
Only the subset needed for OND800: initialize, create sender, send UYVY frames, destroy.
"""

import ctypes
import ctypes.util
from dataclasses import dataclass

_lib = ctypes.CDLL("/usr/local/lib/libndi.so.6")

# ---------------------------------------------------------------------------
# NDI structs (from Processing.NDI.structs.h)
# ---------------------------------------------------------------------------

NDIlib_FourCC_UYVY = (ord('U') | (ord('Y') << 8) | (ord('V') << 16) | (ord('Y') << 24))

class NDIlib_send_create_t(ctypes.Structure):
    _fields_ = [
        ("p_ndi_name",    ctypes.c_char_p),   # NDI stream name
        ("p_groups",      ctypes.c_char_p),   # NULL = default group
        ("clock_video",   ctypes.c_bool),     # True = SDK clocks the video
        ("clock_audio",   ctypes.c_bool),
    ]


class NDIlib_video_frame_v2_t(ctypes.Structure):
    _fields_ = [
        ("xres",               ctypes.c_int),
        ("yres",               ctypes.c_int),
        ("FourCC",             ctypes.c_uint),
        ("frame_rate_N",       ctypes.c_int),
        ("frame_rate_D",       ctypes.c_int),
        ("picture_aspect_ratio", ctypes.c_float),
        ("frame_format_type",  ctypes.c_int),   # 1 = progressive
        ("timecode",           ctypes.c_int64),
        ("p_data",             ctypes.c_void_p),
        ("line_stride_or_size", ctypes.c_int),
        ("p_metadata",         ctypes.c_char_p),
        ("timestamp",          ctypes.c_int64),
    ]

# NDI frame format: progressive = 1
NDIlib_frame_format_type_progressive = 1
# timecode: use NDI's auto value
NDIlib_send_timecode_synthesize = ctypes.c_int64(0x8000000000000000).value

# ---------------------------------------------------------------------------
# Function signatures
# ---------------------------------------------------------------------------

_lib.NDIlib_initialize.restype = ctypes.c_bool
_lib.NDIlib_initialize.argtypes = []

_lib.NDIlib_destroy.restype = None
_lib.NDIlib_destroy.argtypes = []

_lib.NDIlib_send_create.restype = ctypes.c_void_p
_lib.NDIlib_send_create.argtypes = [ctypes.POINTER(NDIlib_send_create_t)]

_lib.NDIlib_send_destroy.restype = None
_lib.NDIlib_send_destroy.argtypes = [ctypes.c_void_p]

_lib.NDIlib_send_send_video_v2.restype = None
_lib.NDIlib_send_send_video_v2.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(NDIlib_video_frame_v2_t),
]

_lib.NDIlib_send_get_no_connections.restype = ctypes.c_int
_lib.NDIlib_send_get_no_connections.argtypes = [ctypes.c_void_p, ctypes.c_int]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize() -> bool:
    return bool(_lib.NDIlib_initialize())


def destroy():
    _lib.NDIlib_destroy()


class NDISender:
    """Send UYVY video frames over NDI."""

    def __init__(self, name: str, clock_video: bool = True):
        cfg = NDIlib_send_create_t(
            p_ndi_name=name.encode(),
            p_groups=None,
            clock_video=clock_video,
            clock_audio=False,
        )
        self._handle = _lib.NDIlib_send_create(ctypes.byref(cfg))
        if not self._handle:
            raise RuntimeError(f"NDIlib_send_create failed for '{name}'")
        self._name = name

    def destroy(self):
        if self._handle:
            _lib.NDIlib_send_destroy(self._handle)
            self._handle = None

    def send_uyvy(self, data: bytes, width: int, height: int,
                  fps_n: int = 30000, fps_d: int = 1001):
        """Send one UYVY frame. data must be width*height*2 bytes."""
        buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        frame = NDIlib_video_frame_v2_t(
            xres=width,
            yres=height,
            FourCC=NDIlib_FourCC_UYVY,
            frame_rate_N=fps_n,
            frame_rate_D=fps_d,
            picture_aspect_ratio=float(width) / float(height),
            frame_format_type=NDIlib_frame_format_type_progressive,
            timecode=NDIlib_send_timecode_synthesize,
            p_data=ctypes.cast(buf, ctypes.c_void_p),
            line_stride_or_size=width * 2,
            p_metadata=None,
            timestamp=0,
        )
        _lib.NDIlib_send_send_video_v2(self._handle, ctypes.byref(frame))

    @property
    def connections(self) -> int:
        return _lib.NDIlib_send_get_no_connections(self._handle, 0)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.destroy()
