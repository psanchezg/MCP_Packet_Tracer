"""Tests for MCP resource data validity."""

from packet_tracer_mcp.infrastructure.catalog.aliases import MODEL_ALIASES
from packet_tracer_mcp.infrastructure.catalog.cables import CABLE_TYPES
from packet_tracer_mcp.infrastructure.catalog.devices import ALL_MODELS
from packet_tracer_mcp.infrastructure.catalog.templates import list_templates
from packet_tracer_mcp.shared.constants import CAPABILITIES


class TestDeviceCatalog:
    def test_has_models(self):
        assert len(ALL_MODELS) >= 50

    def test_router_2911_exists(self):
        assert "2911" in ALL_MODELS

    def test_additional_models_exist(self):
        assert "2811" in ALL_MODELS
        assert "Hub-PT" in ALL_MODELS
        assert "SMARTPHONE-PT" in ALL_MODELS
        assert "WLC-2504" in ALL_MODELS

    def test_each_model_has_ports_when_expected(self):
        portless_models = {
            "Tablet-PT",
            "TabletPC-PT",
            "SMARTPHONE-PT",
            "Analog-Phone-PT",
            "WirelessEndDevice-PT",
            "Cell Tower",
            "Power Distribution Device",
        }
        for name, model in ALL_MODELS.items():
            if name not in portless_models:
                assert len(model.ports) > 0, f"{name} has no ports"

    def test_pc_exists(self):
        assert "PC-PT" in ALL_MODELS


class TestCableCatalog:
    def test_has_cable_types(self):
        assert len(CABLE_TYPES) > 0

    def test_straight_cable_exists(self):
        assert "straight" in CABLE_TYPES


class TestAliases:
    def test_has_aliases(self):
        assert len(MODEL_ALIASES) > 0

    def test_new_aliases_resolve(self):
        assert MODEL_ALIASES["smartphone"] == "SMARTPHONE-PT"
        assert MODEL_ALIASES["hub"] == "Hub-PT"
        assert MODEL_ALIASES["2811"] == "2811"
        assert MODEL_ALIASES["home gateway"] == "Home Gateway"


class TestTemplates:
    def test_has_templates(self):
        templates = list_templates()
        assert len(templates) >= 9

    def test_multi_lan_template(self):
        templates = list_templates()
        keys = [template.key.value for template in templates]
        assert "multi_lan" in keys


class TestCapabilities:
    def test_has_version(self):
        assert "version" in CAPABILITIES
        assert CAPABILITIES["version"] == "0.5.0"

    def test_has_routing(self):
        assert "routing" in CAPABILITIES
        assert "static" in CAPABILITIES["routing"]
        assert "ospf" in CAPABILITIES["routing"]
        assert "rip" in CAPABILITIES["routing"]
        assert "eigrp" in CAPABILITIES["routing"]

    def test_has_features(self):
        assert "features" in CAPABILITIES
        assert "dhcp" in CAPABILITIES["features"]
