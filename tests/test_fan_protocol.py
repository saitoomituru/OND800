import unittest

from streamer.fan_protocol import FanProtocolError, parse_self_report


def valid_packet():
    return {
        "event_schema_version": "1.0.0",
        "uuid": "FAN-AC-0001",
        "role": "light",
        "display_name": "照明左",
        "capabilities": [{"event": "LIGHT_ON", "params": {}}],
        "mutex_group": None,
        "mutex_with": [],
        "base_recast_ms": 0,
        "cooldown_ms": 0,
        "location_hint": "スタジオA",
    }


class FanProtocolTests(unittest.TestCase):
    def test_accepts_supported_schema(self):
        report = parse_self_report(valid_packet())
        self.assertEqual(report.uuid, "FAN-AC-0001")
        self.assertEqual(report.capabilities[0].event, "LIGHT_ON")

    def test_accepts_compatible_minor_version(self):
        packet = valid_packet()
        packet["event_schema_version"] = "1.9.0"
        self.assertEqual(parse_self_report(packet).event_schema_version, "1.9.0")

    def test_rejects_missing_schema_by_default(self):
        packet = valid_packet()
        del packet["event_schema_version"]
        with self.assertRaisesRegex(FanProtocolError, "legacy_schema_disabled"):
            parse_self_report(packet)

    def test_allows_legacy_only_when_explicit(self):
        packet = valid_packet()
        del packet["event_schema_version"]
        report = parse_self_report(packet, allow_legacy_unversioned=True)
        self.assertEqual(report.event_schema_version, "0.0.0-legacy")

    def test_rejects_unknown_major(self):
        packet = valid_packet()
        packet["event_schema_version"] = "2.0.0"
        with self.assertRaisesRegex(FanProtocolError, "unsupported_schema"):
            parse_self_report(packet)

    def test_rejects_hardware_primitive_name(self):
        packet = valid_packet()
        packet["capabilities"][0]["event"] = "GPIO_PIN_4_HIGH_500ms"
        with self.assertRaisesRegex(FanProtocolError, "invalid_event_name"):
            parse_self_report(packet)

    def test_rejects_duplicate_capability(self):
        packet = valid_packet()
        packet["capabilities"].append({"event": "LIGHT_ON", "params": {}})
        with self.assertRaisesRegex(FanProtocolError, "duplicate event"):
            parse_self_report(packet)


if __name__ == "__main__":
    unittest.main()
