"""Tests for Jinja2 configuration templates."""
import pytest
from src.packet_tracer_mcp.domain.services.template_engine import (
    list_available_templates,
    render_template,
)


class TestTemplateDiscovery:
    def test_list_templates_returns_all(self):
        templates = list_available_templates()
        assert len(templates) == 8
        assert "ospf_basic" in templates
        assert "nat_overload" in templates

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="not found"):
            render_template("nonexistent", {})


class TestOSPFTemplate:
    def test_basic_ospf(self):
        lines = render_template("ospf_basic", {
            "process_id": 1,
            "router_id": "1.1.1.1",
            "networks": [{"network": "192.168.1.0", "wildcard": "0.0.0.255", "area": 0}],
            "passive_interfaces": [],
        })
        text = "\n".join(lines)
        assert "router ospf 1" in text
        assert "router-id 1.1.1.1" in text
        assert "network 192.168.1.0 0.0.0.255 area 0" in text

    def test_ospf_with_passive(self):
        lines = render_template("ospf_basic", {
            "process_id": 10,
            "router_id": "",
            "networks": [{"network": "10.0.0.0", "wildcard": "0.0.0.3", "area": 0}],
            "passive_interfaces": ["GigabitEthernet0/1"],
        })
        text = "\n".join(lines)
        assert "passive-interface GigabitEthernet0/1" in text


class TestEIGRPTemplate:
    def test_eigrp_named(self):
        lines = render_template("eigrp_named", {
            "name": "CORP",
            "as_number": 100,
            "router_id": "2.2.2.2",
            "networks": [{"network": "192.168.0.0", "wildcard": "0.0.0.255"}],
            "af": "ipv4",
        })
        text = "\n".join(lines)
        assert "router eigrp CORP" in text
        assert "address-family ipv4 autonomous-system 100" in text
        assert "no auto-summary" in text


class TestVLANTemplate:
    def test_vlan_trunk(self):
        lines = render_template("vlan_trunk", {
            "vlans": [{"id": 10, "name": "SALES"}, {"id": 20, "name": "IT"}],
            "trunk_interfaces": ["GigabitEthernet0/1"],
            "access_ports": [{"interface": "FastEthernet0/1", "vlan_id": 10}],
        })
        text = "\n".join(lines)
        assert "vlan 10" in text
        assert "name SALES" in text
        assert "switchport mode trunk" in text
        assert "switchport mode access" in text
        assert "switchport access vlan 10" in text


class TestHSRPTemplate:
    def test_hsrp_pair(self):
        lines = render_template("hsrp_pair", {
            "interface": "GigabitEthernet0/0",
            "group": 1,
            "virtual_ip": "192.168.1.1",
            "priority": 110,
            "preempt": True,
            "track_interface": "GigabitEthernet0/1",
        })
        text = "\n".join(lines)
        assert "standby 1 ip 192.168.1.1" in text
        assert "standby 1 priority 110" in text
        assert "standby 1 preempt" in text
        assert "standby 1 track" in text


class TestNATTemplate:
    def test_nat_overload(self):
        lines = render_template("nat_overload", {
            "inside_interface": "GigabitEthernet0/0",
            "outside_interface": "GigabitEthernet0/1",
            "acl_number": 1,
            "source_network": "192.168.1.0",
            "source_wildcard": "0.0.0.255",
        })
        text = "\n".join(lines)
        assert "access-list 1 permit 192.168.1.0 0.0.0.255" in text
        assert "ip nat inside" in text
        assert "ip nat outside" in text
        assert "overload" in text


class TestACLTemplate:
    def test_acl_dmz(self):
        lines = render_template("acl_dmz", {
            "acl_name": "DMZ_IN",
            "rules": [{
                "action": "permit",
                "protocol": "tcp",
                "source": "any",
                "source_wildcard": "",
                "destination": "host 192.168.1.100",
                "destination_wildcard": "",
                "port": "80",
            }],
            "interface": "GigabitEthernet0/0",
            "direction": "in",
        })
        text = "\n".join(lines)
        assert "ip access-list extended DMZ_IN" in text
        assert "permit tcp" in text
        assert "deny ip any any" in text
        assert "ip access-group DMZ_IN in" in text


class TestDHCPTemplate:
    def test_dhcp_server(self):
        lines = render_template("dhcp_server", {
            "pools": [{
                "name": "LAN_POOL",
                "network": "192.168.1.0",
                "mask": "255.255.255.0",
                "gateway": "192.168.1.1",
                "dns": "8.8.8.8",
                "excluded_start": "192.168.1.1",
                "excluded_end": "192.168.1.10",
                "lease_days": 7,
            }],
        })
        text = "\n".join(lines)
        assert "ip dhcp pool LAN_POOL" in text
        assert "network 192.168.1.0 255.255.255.0" in text
        assert "default-router 192.168.1.1" in text
        assert "ip dhcp excluded-address 192.168.1.1 192.168.1.10" in text
        assert "lease 7" in text


class TestSTPTemplate:
    def test_stp_rapid(self):
        lines = render_template("stp_rapid", {
            "mode": "rapid-pvst",
            "root_vlan": 1,
            "root_priority": 4096,
            "portfast_interfaces": ["FastEthernet0/1", "FastEthernet0/2"],
        })
        text = "\n".join(lines)
        assert "spanning-tree mode rapid-pvst" in text
        assert "spanning-tree portfast" in text
        assert "bpduguard enable" in text
