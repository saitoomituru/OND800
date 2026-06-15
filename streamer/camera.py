"""Camera detection and format selection for OND800."""

import subprocess
import re
from dataclasses import dataclass, field


@dataclass(order=True)
class Format:
    """A single camera format/resolution/fps combination."""
    # sort key: prefer 30fps, then highest area, then highest fps
    _sort_key: tuple = field(init=False, repr=False, compare=True)

    pixelformat: str  # 'MJPG' or 'YUYV'
    width: int
    height: int
    fps: float

    def __post_init__(self):
        hits_30 = 1 if self.fps >= 30 else 0
        self._sort_key = (hits_30, self.width * self.height, self.fps)

    @property
    def area(self) -> int:
        return self.width * self.height

    def __repr__(self):
        return f"{self.pixelformat} {self.width}x{self.height}@{self.fps:.0f}fps"


# Format priority: MJPG can carry HD at 30fps over USB2, YUYV cannot.
_FORMAT_RANK = {"MJPG": 0, "YUYV": 1, "UYVY": 2, "NV12": 3}


def list_formats(device: str) -> list[Format]:
    """Return all formats supported by *device* via v4l2-ctl."""
    try:
        out = subprocess.check_output(
            ["v4l2-ctl", "-d", device, "--list-formats-ext"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    formats: list[Format] = []
    current_fmt = None
    current_size = None

    for line in out.splitlines():
        m = re.search(r"'(\w{4})'", line)
        if m:
            current_fmt = m.group(1)
            continue
        m = re.search(r"Size: Discrete (\d+)x(\d+)", line)
        if m:
            current_size = (int(m.group(1)), int(m.group(2)))
            continue
        m = re.search(r"Interval: Discrete [\d.]+s \(([\d.]+) fps\)", line)
        if m and current_fmt and current_size:
            fps = float(m.group(1))
            formats.append(Format(current_fmt, current_size[0], current_size[1], fps))

    return formats


def best_format(formats: list[Format]) -> Format | None:
    """
    Select the best format following OND800 streaming policy:
      1. 30fps @ highest resolution (MJPG preferred)
      2. If no 30fps exists: highest resolution within spec (fps follows)
    """
    if not formats:
        return None

    # Group by pixel format priority, then apply sort within each
    def rank(f: Format) -> tuple:
        hits_30 = 1 if f.fps >= 30 else 0
        fmt_rank = _FORMAT_RANK.get(f.pixelformat, 99)
        return (hits_30, f.area, f.fps, -fmt_rank)

    return max(formats, key=rank)


@dataclass
class Camera:
    device: str       # e.g. '/dev/video0'
    name: str         # human-readable (from udev or v4l2)
    bus_id: str = ""  # USB bus+device id for stable identification

    def formats(self) -> list[Format]:
        return list_formats(self.device)

    def best_format(self) -> Format | None:
        return best_format(self.formats())


def _is_capture_device(device: str) -> bool:
    """Return True only if the device's own caps include Video Capture (not metadata-only)."""
    try:
        out = subprocess.check_output(
            ["v4l2-ctl", "-d", device, "--info"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        # "Device Caps" section lists what *this* node actually does.
        # Metadata-only nodes show "Metadata Capture" but not "Video Capture" there.
        in_device_caps = False
        for line in out.splitlines():
            if "Device Caps" in line:
                in_device_caps = True
            if in_device_caps and "Video Capture" in line:
                return True
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def discover_cameras() -> list[Camera]:
    """Return UVC cameras currently visible to v4l2."""
    try:
        out = subprocess.check_output(
            ["v4l2-ctl", "--list-devices"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    cameras: list[Camera] = []
    current_name = None
    seen_devices: set[str] = set()

    for line in out.splitlines():
        if not line.startswith("\t") and line.strip():
            current_name = line.split("(")[0].strip()
        elif line.startswith("\t") and current_name:
            dev = line.strip()
            # only /dev/videoN that aren't internal Pi ISP/HEVC devices
            if re.match(r"^/dev/video\d+$", dev) and dev not in seen_devices:
                # skip internal Pi5 ISP devices (video19+)
                num = int(re.search(r"\d+", dev).group())
                if num < 10 and _is_capture_device(dev):
                    seen_devices.add(dev)
                    cameras.append(Camera(device=dev, name=current_name))

    return cameras
