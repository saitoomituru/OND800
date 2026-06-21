"""FAN800イベント契約の機種非依存検証。

BLE transportから独立させ、実機接続前でも自己申告パケットの互換性と
最小フィールドを検証できるようにする。
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


SUPPORTED_EVENT_SCHEMA_MAJOR = 1
EVENT_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")


class FanProtocolError(ValueError):
    """FAN800パケットを安全に受理できない場合の例外。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class FanCapability:
    event: str
    params: Mapping[str, Any]


@dataclass(frozen=True)
class FanSelfReport:
    event_schema_version: str
    uuid: str
    role: str
    display_name: str
    capabilities: tuple[FanCapability, ...]
    mutex_group: str | None
    mutex_with: tuple[str, ...]
    base_recast_ms: int
    cooldown_ms: int
    location_hint: str | None


def _schema_major(version: str) -> int:
    match = re.fullmatch(r"(0|[1-9][0-9]*)\.[0-9]+\.[0-9]+", version)
    if not match:
        raise FanProtocolError("unsupported_schema", "invalid semantic version")
    return int(match.group(1))


def parse_self_report(
    packet: Mapping[str, Any], *, allow_legacy_unversioned: bool = False
) -> FanSelfReport:
    """自己申告パケットを検証し、不変データへ変換する。"""

    version = packet.get("event_schema_version")
    if version is None:
        if not allow_legacy_unversioned:
            raise FanProtocolError("legacy_schema_disabled")
        version = "0.0.0-legacy"
    elif not isinstance(version, str) or _schema_major(version) != SUPPORTED_EVENT_SCHEMA_MAJOR:
        raise FanProtocolError("unsupported_schema")

    uuid = _required_string(packet, "uuid")
    role = _required_string(packet, "role")
    display_name = _required_string(packet, "display_name")
    raw_capabilities = packet.get("capabilities")
    if not isinstance(raw_capabilities, list) or not raw_capabilities:
        raise FanProtocolError("invalid_self_report", "capabilities must be a non-empty list")

    capabilities: list[FanCapability] = []
    seen_events: set[str] = set()
    for item in raw_capabilities:
        if not isinstance(item, Mapping):
            raise FanProtocolError("invalid_self_report", "capability must be an object")
        event = _required_string(item, "event")
        if not EVENT_NAME_PATTERN.fullmatch(event):
            raise FanProtocolError("invalid_event_name", event)
        if event in seen_events:
            raise FanProtocolError("invalid_self_report", f"duplicate event: {event}")
        params = item.get("params", {})
        if not isinstance(params, Mapping):
            raise FanProtocolError("invalid_self_report", f"params must be an object: {event}")
        seen_events.add(event)
        capabilities.append(FanCapability(event=event, params=dict(params)))

    return FanSelfReport(
        event_schema_version=version,
        uuid=uuid,
        role=role,
        display_name=display_name,
        capabilities=tuple(capabilities),
        mutex_group=_optional_string(packet, "mutex_group"),
        mutex_with=_string_tuple(packet.get("mutex_with", []), "mutex_with"),
        base_recast_ms=_nonnegative_int(packet, "base_recast_ms"),
        cooldown_ms=_nonnegative_int(packet, "cooldown_ms"),
        location_hint=_optional_string(packet, "location_hint"),
    )


def _required_string(packet: Mapping[str, Any], key: str) -> str:
    value = packet.get(key)
    if not isinstance(value, str) or not value:
        raise FanProtocolError("invalid_self_report", f"{key} must be a non-empty string")
    return value


def _optional_string(packet: Mapping[str, Any], key: str) -> str | None:
    value = packet.get(key)
    if value is not None and not isinstance(value, str):
        raise FanProtocolError("invalid_self_report", f"{key} must be a string or null")
    return value


def _nonnegative_int(packet: Mapping[str, Any], key: str) -> int:
    value = packet.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FanProtocolError("invalid_self_report", f"{key} must be a non-negative integer")
    return value


def _string_tuple(value: Any, key: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise FanProtocolError("invalid_self_report", f"{key} must be a string list")
    return tuple(value)
