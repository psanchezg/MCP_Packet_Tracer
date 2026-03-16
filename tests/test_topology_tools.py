"""Tests for topology intelligence engine."""
import json
import pytest
from src.packet_tracer_mcp.domain.services.topology_analyzer import (
    analyze_topology,
    suggest_improvements,
    calculate_addressing,
    validate_config_lines,
    validate_topology_deep,
)
from src.packet_tracer_mcp.domain.models.plans import TopologyPlan, DevicePlan, LinkPlan
from src.packet_tracer_mcp.domain.services.orchestrator import plan_from_request
from src.packet_tracer_mcp.domain.models.requests import TopologyRequest
from src.packet_tracer_mcp.shared.enums import RoutingProtocol


class TestAnalyzeTopology:
    def test_spanish_corporate_network(self):
        result = analyze_topology("red corporativa con 3 sucursales y servidor web")
        assert len(result.sites) >= 3  # 3 branches + auto HQ
        assert result.has_wan is True  # multi-site

    def test_english_simple(self):
        result = analyze_topology("simple network with 2 routers and 5 PCs")
        assert result.total_devices > 0
        assert len(result.subnets) > 0

    def test_hq_branch(self):
        result = analyze_topology("headquarters with 2 branches connected via WAN, OSPF routing")
        assert result.routing_protocol == "OSPF"
        assert result.has_wan is True
        assert any(s.type == "HQ" for s in result.sites)

    def test_dmz_detection(self):
        result = analyze_topology("network with DMZ and web server")
        assert result.has_dmz is True

    def test_redundancy_detection(self):
        result = analyze_topology("red con alta disponibilidad y redundancia")
        assert result.has_redundancy is True

    def test_suggested_models_small(self):
        result = analyze_topology("small office with 1 router and 3 PCs")
        assert "router" in result.suggested_models
        assert "switch" in result.suggested_models

    def test_subnets_generated(self):
        result = analyze_topology("2 routers, 5 PCs")
        assert len(result.subnets) > 0
        for subnet in result.subnets:
            assert "network" in subnet


class TestSuggestImprovements:
    def test_basic_plan_has_suggestions(self, basic_plan):
        improvements = suggest_improvements(basic_plan)
        # Should be a list (may or may not have suggestions for a valid plan)
        assert isinstance(improvements, list)

    def test_no_dhcp_flagged(self):
        plan = TopologyPlan(
            devices=[
                DevicePlan(name="R1", model="2911", category="router"),
                DevicePlan(name="PC1", model="PC-PT", category="pc"),
            ],
            links=[LinkPlan(device_a="R1", port_a="Gig0/0", device_b="PC1", port_b="Fa0")]
        )
        improvements = suggest_improvements(plan)
        categories = [i.category for i in improvements]
        assert "best_practice" in categories  # no DHCP warning

    def test_orphaned_device_detected(self):
        plan = TopologyPlan(
            devices=[
                DevicePlan(name="R1", model="2911", category="router"),
                DevicePlan(name="R2", model="2911", category="router"),  # no links
            ],
            links=[]
        )
        improvements = suggest_improvements(plan)
        orphan_msgs = [i for i in improvements if i.category == "connectivity"]
        assert len(orphan_msgs) >= 2  # both devices orphaned

    def test_multiple_routers_no_routing(self):
        plan = TopologyPlan(
            devices=[
                DevicePlan(name="R1", model="2911", category="router", interfaces={"Gig0/0": "10.0.0.1/30"}),
                DevicePlan(name="R2", model="2911", category="router", interfaces={"Gig0/0": "10.0.0.2/30"}),
            ],
            links=[LinkPlan(device_a="R1", port_a="Gig0/0", device_b="R2", port_b="Gig0/0")]
        )
        improvements = suggest_improvements(plan)
        routing_msgs = [i for i in improvements if "routing" in i.message.lower()]
        assert len(routing_msgs) > 0


class TestCalculateAddressing:
    def test_single_site(self):
        sites = [{"name": "Office", "routers": 1, "pcs": 3}]
        result = calculate_addressing(sites)
        assert len(result.devices) > 0
        assert "Office-R1" in result.devices

    def test_multi_site_wan_links(self):
        sites = [
            {"name": "HQ", "routers": 1, "pcs": 5},
            {"name": "Branch", "routers": 1, "pcs": 3},
        ]
        result = calculate_addressing(sites)
        assert len(result.summary) >= 2  # At least LAN + WAN entries

    def test_ipv6_dual_stack(self):
        sites = [{"name": "Test", "routers": 1, "pcs": 2}]
        result = calculate_addressing(sites, enable_ipv6=True)
        for ifaces in result.devices.values():
            for entry in ifaces.values():
                if entry.ipv6:
                    assert "2001:" in entry.ipv6
                    break

    def test_vlans_included(self):
        sites = [{"name": "Main", "routers": 1, "pcs": 2}]
        vlans = [{"id": 10, "name": "SALES"}, {"id": 20, "name": "IT"}]
        result = calculate_addressing(sites, vlans=vlans)
        assert len(result.vlans) == 2

    def test_loopback_assigned(self):
        sites = [{"name": "Site", "routers": 1, "pcs": 1}]
        result = calculate_addressing(sites)
        r1_ifaces = result.devices.get("Site-R1", {})
        assert "Loopback0" in r1_ifaces


class TestValidateConfigLines:
    def test_ip_conflict_detected(self, basic_plan):
        # Get an IP that's already in the plan
        r1 = basic_plan.device_by_name("R1")
        if r1 and r1.interfaces:
            existing_ip = list(r1.interfaces.values())[0].split("/")[0]
            config = [
                "interface GigabitEthernet0/0",
                f" ip address {existing_ip} 255.255.255.0",
                " no shutdown",
            ]
            errors = validate_config_lines("R2", config, basic_plan)
            ip_errors = [e for e in errors if e.rule == "ip_conflict"]
            assert len(ip_errors) > 0

    def test_missing_no_shutdown(self, basic_plan):
        config = [
            "interface GigabitEthernet0/1",
            " ip address 172.16.0.1 255.255.255.0",
        ]
        errors = validate_config_lines("R1", config, basic_plan)
        no_shut_warns = [e for e in errors if e.rule == "missing_no_shutdown"]
        assert len(no_shut_warns) > 0

    def test_valid_config_no_errors(self, basic_plan):
        config = [
            "interface GigabitEthernet0/1",
            " ip address 172.16.0.1 255.255.255.0",
            " no shutdown",
        ]
        errors = validate_config_lines("R1", config, basic_plan)
        real_errors = [e for e in errors if e.severity == "error"]
        assert len(real_errors) == 0


class TestValidateTopologyDeep:
    def test_valid_plan_passes(self, basic_plan):
        errors = validate_topology_deep(basic_plan)
        critical = [e for e in errors if e.severity == "error"]
        # Basic plan should not have orphaned devices
        orphaned = [e for e in critical if e.rule == "orphaned_device"]
        assert len(orphaned) == 0

    def test_orphaned_device(self):
        plan = TopologyPlan(
            devices=[
                DevicePlan(name="R1", model="2911", category="router"),
                DevicePlan(name="R2", model="2911", category="router"),
            ],
            links=[]
        )
        errors = validate_topology_deep(plan)
        orphaned = [e for e in errors if e.rule == "orphaned_device"]
        assert len(orphaned) == 2
