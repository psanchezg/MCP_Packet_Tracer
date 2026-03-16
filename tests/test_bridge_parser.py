"""Tests for _extract_ptbuilder_calls -- the JS statement parser."""
from src.packet_tracer_mcp.adapters.mcp.tools._bridge_helpers import (
    _extract_ptbuilder_calls,
)


class TestExtractPTBuilderCalls:
    def test_single_adddevice(self):
        script = 'addDevice("R1", "2911", 100, 200);'
        result = _extract_ptbuilder_calls(script)
        assert result == ['addDevice("R1", "2911", 100, 200)']

    def test_single_addlink(self):
        script = (
            'addLink("R1", "GigabitEthernet0/0", '
            '"SW1", "GigabitEthernet0/1", "straight");'
        )
        result = _extract_ptbuilder_calls(script)
        assert len(result) == 1
        assert result[0].startswith('addLink(')

    def test_multiline_configuredevice(self):
        """The core bug fix -- multiline calls must be one entry."""
        script = """configureDevice("R1", [
  "hostname R1",
  "interface GigabitEthernet0/0",
  "ip address 192.168.1.1 255.255.255.0",
  "no shutdown"
]);"""
        result = _extract_ptbuilder_calls(script)
        assert len(result) == 1
        assert result[0].startswith('configureDevice("R1"')
        assert "hostname R1" in result[0]
        assert "no shutdown" in result[0]

    def test_full_topology_script(self):
        """Three calls in sequence must produce three entries."""
        script = """
addDevice("R1", "2911", 100, 200);
addDevice("SW1", "2960-24TT", 300, 200);
addLink("R1", "GigabitEthernet0/0", "SW1", "GigabitEthernet0/1", "straight");
"""
        result = _extract_ptbuilder_calls(script)
        assert len(result) == 3
        assert result[0].startswith('addDevice("R1"')
        assert result[1].startswith('addDevice("SW1"')
        assert result[2].startswith('addLink(')

    def test_skips_comments(self):
        """Single-line comments must be ignored."""
        script = """
// PHASE 1: DEVICES
addDevice("R1", "2911", 100, 200);
// PHASE 2: LINKS
addLink("R1", "GigabitEthernet0/0", "SW1", "GigabitEthernet0/1", "straight");
"""
        result = _extract_ptbuilder_calls(script)
        assert len(result) == 2
        assert all(not r.startswith("//") for r in result)

    def test_skips_blank_lines(self):
        script = '\n\n\naddDevice("R1", "2911", 100, 200);\n\n\n'
        result = _extract_ptbuilder_calls(script)
        assert len(result) == 1

    def test_inline_comment_stripped(self):
        script = 'addDevice("R1", "2911", 100, 200); // core router'
        result = _extract_ptbuilder_calls(script)
        assert len(result) == 1
        assert "//" not in result[0]

    def test_configuredevice_with_ospf(self):
        """Real-world OSPF config -- many lines inside the array."""
        script = """configureDevice("R1", [
  "hostname R1",
  "router ospf 1",
  "network 192.168.1.0 0.0.0.255 area 0",
  "network 10.0.0.0 0.0.0.3 area 0",
  "passive-interface GigabitEthernet0/2"
]);"""
        result = _extract_ptbuilder_calls(script)
        assert len(result) == 1
        assert "router ospf 1" in result[0]
        assert "passive-interface" in result[0]

    def test_empty_script(self):
        assert _extract_ptbuilder_calls("") == []

    def test_only_comments(self):
        script = "// comment 1\n// comment 2\n"
        assert _extract_ptbuilder_calls(script) == []

    def test_preserves_ip_addresses(self):
        """IP addresses with dots must not be corrupted."""
        script = """configureDevice("R1", [
  "ip address 192.168.100.1 255.255.255.252",
  "no shutdown"
]);"""
        result = _extract_ptbuilder_calls(script)
        assert "192.168.100.1" in result[0]
        assert "255.255.255.252" in result[0]
