"""Tests for scenario presets."""
import pytest
from packet_tracer_mcp.domain.services.presets import (
    list_presets,
    build_preset_request,
    PRESET_CATALOG,
)
from packet_tracer_mcp.domain.services.orchestrator import plan_from_request


class TestPresetListing:
    def test_list_presets_returns_all(self):
        presets = list_presets()
        assert len(presets) == 8

    def test_each_preset_has_key_name_description(self):
        for p in list_presets():
            assert "key" in p
            assert "name" in p
            assert "description" in p
            assert len(p["description"]) > 10


class TestPresetBuild:
    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            build_preset_request("nonexistent_preset")

    def test_customize_overrides(self):
        req = build_preset_request("small_office", {"pcs_per_lan": 10})
        assert req.pcs_per_lan == 10

    @pytest.mark.parametrize("preset_name", list(PRESET_CATALOG.keys()))
    def test_preset_produces_valid_plan(self, preset_name):
        request = build_preset_request(preset_name)
        plan, validation = plan_from_request(request)
        assert validation.is_valid, f"Preset '{preset_name}' produced invalid plan: {validation.error_messages()}"
        assert len(plan.devices) > 0
        assert len(plan.links) > 0

    @pytest.mark.parametrize("preset_name", list(PRESET_CATALOG.keys()))
    def test_preset_has_devices_and_links(self, preset_name):
        request = build_preset_request(preset_name)
        plan, _ = plan_from_request(request)
        routers = plan.devices_by_category("router")
        assert len(routers) >= 1
