"""Tests for RIP and EIGRP routing protocol support."""
from src.packet_tracer_mcp.domain.services.orchestrator import plan_from_request
from src.packet_tracer_mcp.infrastructure.generator.cli_config_generator import generate_all_configs


class TestRIPRouting:
    def test_rip_configs_generated(self, rip_request):
        plan, validation = plan_from_request(rip_request)
        assert validation.is_valid
        assert len(plan.rip_configs) > 0

    def test_rip_version_2(self, rip_request):
        plan, _ = plan_from_request(rip_request)
        for cfg in plan.rip_configs:
            assert cfg.version == 2

    def test_rip_no_auto_summary(self, rip_request):
        plan, _ = plan_from_request(rip_request)
        for cfg in plan.rip_configs:
            assert cfg.no_auto_summary is True

    def test_rip_has_networks(self, rip_request):
        plan, _ = plan_from_request(rip_request)
        for cfg in plan.rip_configs:
            assert len(cfg.networks) > 0

    def test_rip_cli_config(self, rip_request):
        plan, _ = plan_from_request(rip_request)
        configs = generate_all_configs(plan)
        # At least one router should have RIP config
        has_rip = any("router rip" in cfg for cfg in configs.values())
        assert has_rip

    def test_rip_cli_has_version(self, rip_request):
        plan, _ = plan_from_request(rip_request)
        configs = generate_all_configs(plan)
        has_version = any("version 2" in cfg for cfg in configs.values())
        assert has_version

    def test_rip_no_static_routes(self, rip_request):
        plan, _ = plan_from_request(rip_request)
        assert len(plan.static_routes) == 0


class TestEIGRPRouting:
    def test_eigrp_configs_generated(self, eigrp_request):
        plan, validation = plan_from_request(eigrp_request)
        assert validation.is_valid
        assert len(plan.eigrp_configs) > 0

    def test_eigrp_default_as(self, eigrp_request):
        plan, _ = plan_from_request(eigrp_request)
        for cfg in plan.eigrp_configs:
            assert cfg.as_number == 100

    def test_eigrp_no_auto_summary(self, eigrp_request):
        plan, _ = plan_from_request(eigrp_request)
        for cfg in plan.eigrp_configs:
            assert cfg.no_auto_summary is True

    def test_eigrp_has_networks(self, eigrp_request):
        plan, _ = plan_from_request(eigrp_request)
        for cfg in plan.eigrp_configs:
            assert len(cfg.networks) > 0
            for net in cfg.networks:
                assert "network" in net
                assert "wildcard" in net

    def test_eigrp_custom_as(self):
        from src.packet_tracer_mcp.domain.models.requests import TopologyRequest
        from src.packet_tracer_mcp.shared.enums import RoutingProtocol
        request = TopologyRequest(routers=2, pcs_per_lan=2, routing=RoutingProtocol.EIGRP, eigrp_as=200)
        plan, _ = plan_from_request(request)
        for cfg in plan.eigrp_configs:
            assert cfg.as_number == 200

    def test_eigrp_cli_config(self, eigrp_request):
        plan, _ = plan_from_request(eigrp_request)
        configs = generate_all_configs(plan)
        has_eigrp = any("router eigrp" in cfg for cfg in configs.values())
        assert has_eigrp

    def test_eigrp_no_static_routes(self, eigrp_request):
        plan, _ = plan_from_request(eigrp_request)
        assert len(plan.static_routes) == 0
