"""Tests for upgraded validation layer and bridge helpers."""
import json
import pytest
from packet_tracer_mcp.domain.models.plans import (
    TopologyPlan, DevicePlan, LinkPlan, OSPFConfig,
)
from packet_tracer_mcp.domain.services.topology_analyzer import (
    validate_config_lines,
    validate_topology_deep,
)
from packet_tracer_mcp.adapters.mcp.tools._bridge_helpers import (
    record_command,
    pop_last_command,
    clear_command_history,
    save_last_plan,
    load_last_plan,
)


class TestValidateConfigLines:
    def test_detects_ip_conflict(self, basic_plan):
        r1 = basic_plan.device_by_name("R1")
        if r1 and r1.interfaces:
            ip = list(r1.interfaces.values())[0].split("/")[0]
            errors = validate_config_lines("R2", [
                "interface Gig0/0",
                f" ip address {ip} 255.255.255.0",
                " no shutdown",
            ], basic_plan)
            assert any(e.rule == "ip_conflict" for e in errors)

    def test_detects_missing_no_shutdown(self, basic_plan):
        errors = validate_config_lines("R1", [
            "interface GigabitEthernet0/1",
            " ip address 172.16.0.1 255.255.255.0",
        ], basic_plan)
        assert any(e.rule == "missing_no_shutdown" for e in errors)

    def test_detects_acl_applied_not_defined(self, basic_plan):
        errors = validate_config_lines("R1", [
            "interface GigabitEthernet0/0",
            " ip access-group BLOCK_ALL in",
            " no shutdown",
        ], basic_plan)
        assert any(e.rule == "acl_not_defined" for e in errors)

    def test_detects_acl_defined_not_applied(self, basic_plan):
        errors = validate_config_lines("R1", [
            "ip access-list extended UNUSED_ACL",
            " permit ip any any",
        ], basic_plan)
        assert any(e.rule == "acl_not_applied" for e in errors)

    def test_clean_config_no_errors(self, basic_plan):
        errors = validate_config_lines("R1", [
            "interface GigabitEthernet0/1",
            " ip address 172.16.0.1 255.255.255.0",
            " no shutdown",
            " exit",
        ], basic_plan)
        real_errors = [e for e in errors if e.severity == "error"]
        assert len(real_errors) == 0


class TestValidateTopologyDeep:
    def test_orphaned_device_detected(self):
        plan = TopologyPlan(devices=[
            DevicePlan(name="R1", model="2911", category="router"),
            DevicePlan(name="R2", model="2911", category="router"),
        ], links=[])
        errors = validate_topology_deep(plan)
        orphaned = [e for e in errors if e.rule == "orphaned_device"]
        assert len(orphaned) == 2

    def test_single_interface_router_warned(self):
        plan = TopologyPlan(devices=[
            DevicePlan(name="R1", model="2911", category="router",
                       interfaces={"Gig0/0": "10.0.0.1/30"}),
            DevicePlan(name="SW1", model="2960-24TT", category="switch"),
        ], links=[
            LinkPlan(device_a="R1", port_a="Gig0/0", device_b="SW1", port_b="Gig0/1"),
        ])
        errors = validate_topology_deep(plan)
        single_iface = [e for e in errors if e.rule == "single_interface_router"]
        assert len(single_iface) == 1

    def test_subnet_mismatch_detected(self):
        plan = TopologyPlan(devices=[
            DevicePlan(name="R1", model="2911", category="router",
                       interfaces={"Gig0/0": "10.0.0.1/30"}),
            DevicePlan(name="R2", model="2911", category="router",
                       interfaces={"Gig0/0": "10.0.1.2/30"}),
        ], links=[
            LinkPlan(device_a="R1", port_a="Gig0/0", device_b="R2", port_b="Gig0/0"),
        ])
        errors = validate_topology_deep(plan)
        mismatches = [e for e in errors if e.rule == "subnet_mismatch"]
        assert len(mismatches) == 1

    def test_valid_plan_minimal_errors(self, basic_plan):
        errors = validate_topology_deep(basic_plan)
        critical = [e for e in errors if e.rule == "orphaned_device"]
        assert len(critical) == 0


class TestBridgeCommandHistory:
    def test_record_and_pop(self):
        clear_command_history()
        record_command("addDevice('R1','2911',100,100)")
        record_command("addDevice('R2','2911',200,100)")
        assert pop_last_command() == "addDevice('R2','2911',200,100)"
        assert pop_last_command() == "addDevice('R1','2911',100,100)"
        assert pop_last_command() is None

    def test_clear_history(self):
        clear_command_history()
        record_command("test_cmd")
        clear_command_history()
        assert pop_last_command() is None


class TestPlanPersistence:
    def test_save_and_load(self, basic_plan, tmp_path, monkeypatch):
        import packet_tracer_mcp.adapters.mcp.tools._bridge_helpers as bh
        persist_path = tmp_path / "test_plan.json"
        monkeypatch.setattr(bh, "_PLAN_PERSIST_PATH", persist_path)

        plan_json = basic_plan.model_dump_json()
        save_last_plan(plan_json)
        loaded = load_last_plan()
        assert loaded is not None
        assert json.loads(loaded)["devices"] is not None

    def test_load_nonexistent_returns_none(self, tmp_path, monkeypatch):
        import packet_tracer_mcp.adapters.mcp.tools._bridge_helpers as bh
        monkeypatch.setattr(bh, "_PLAN_PERSIST_PATH", tmp_path / "nope.json")
        assert load_last_plan() is None
