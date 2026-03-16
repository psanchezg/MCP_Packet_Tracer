"""Preset tools — pt_list_presets, pt_load_preset."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ....domain.services.explainer import explain_plan
from ....domain.services.orchestrator import plan_from_request
from ....domain.services.presets import build_preset_request, list_presets
from ....infrastructure.generator.cli_config_generator import (
    generate_all_configs,
    generate_pc_config,
)
from ....infrastructure.generator.ptbuilder_generator import generate_full_script
from ....shared.logging import get_logger

logger = get_logger(__name__)


def register_preset_tools(mcp: FastMCP) -> None:
    """Register scenario preset MCP tools."""

    @mcp.tool()
    def pt_list_presets() -> str:
        """
        List all available scenario presets with descriptions.

        Presets are ready-made topologies that generate complete,
        fully wired and configured plans in one call.
        """
        logger.debug("pt_list_presets called")
        presets = list_presets()
        lines: list[str] = ["Available Presets:", ""]
        for p in presets:
            lines.append(f"  **{p['name']}** (key: `{p['key']}`)")
            lines.append(f"    {p['description']}")
            lines.append("")
        return "\n".join(lines)

    @mcp.tool()
    def pt_load_preset(
        preset_name: str,
        customize_json: str = "{}",
    ) -> str:
        """
        Load a scenario preset and generate a complete build plan.

        Returns the full topology with devices, links, IPs, configs,
        and PTBuilder script — ready to deploy.

        Available presets:
        - small_office: 1 router, 1 switch, 5 PCs, DHCP
        - branch_hq: 2 sites, WAN, OSPF, DHCP
        - dmz_network: Router firewall, DMZ servers, internal LAN
        - redundant_core: Dual core, floating static routes
        - full_enterprise: HQ + 2 branches, OSPF, servers
        - ccna_lab_1: Classic CCNA exam topology
        - ccnp_switch_lab: Multi-switch lab, OSPF
        - ipv6_dual_stack: IPv4+IPv6 dual-stack

        Parameters:
        - preset_name: Preset key (e.g. "small_office", "branch_hq")
        - customize_json: Optional JSON overrides, e.g.
          {"routers": 3, "pcs_per_lan": 5, "routing": "eigrp"}
        """
        logger.info("pt_load_preset: %s", preset_name)
        customize = json.loads(customize_json) if customize_json else {}
        request = build_preset_request(preset_name, customize)
        plan, validation = plan_from_request(request)
        explanation = explain_plan(plan)

        parts: list[str] = []
        parts.append(f"PRESET: {preset_name}")
        parts.append("=" * 60)
        parts.append(f"Devices: {len(plan.devices)}")
        parts.append(f"Links: {len(plan.links)}")
        parts.append(f"DHCP Pools: {len(plan.dhcp_pools)}")
        parts.append("")

        if validation.is_valid:
            parts.append("Validation: PASS")
        else:
            parts.append("Validation: FAIL")
            for err in validation.errors:
                parts.append(f"  ERROR [{err.code.value}]: {err.message}")
        parts.append("")

        # Explanation
        parts.append("EXPLANATION")
        parts.append("-" * 40)
        for e in explanation:
            parts.append(f"  {e}")
        parts.append("")

        # Addressing table
        parts.append("ADDRESSING TABLE")
        parts.append("-" * 40)
        for dev in plan.devices:
            if dev.interfaces:
                parts.append(f"{dev.name} ({dev.model}):")
                for iface, ip in dev.interfaces.items():
                    parts.append(f"  {iface}: {ip}")
                if dev.gateway:
                    parts.append(f"  Gateway: {dev.gateway}")
            elif dev.gateway:
                parts.append(f"{dev.name}: DHCP (Gateway: {dev.gateway})")
        parts.append("")

        # Script
        parts.append("PTBUILDER SCRIPT")
        parts.append("-" * 40)
        parts.append(generate_full_script(plan))
        parts.append("")

        # CLI configs
        configs = generate_all_configs(plan)
        parts.append("CLI CONFIGURATIONS")
        parts.append("-" * 40)
        for device_name, cli_block in configs.items():
            parts.append(f"\n--- {device_name} ---")
            parts.append(cli_block)
        pcs = [d for d in plan.devices if d.category in ("pc", "server", "laptop")]
        if pcs:
            parts.append("\n--- Hosts ---")
            for pc in pcs:
                parts.append(generate_pc_config(pc))

        # Plan JSON
        parts.append("")
        parts.append("PLAN JSON")
        parts.append("-" * 40)
        parts.append(plan.model_dump_json(indent=2))

        return "\n".join(parts)
