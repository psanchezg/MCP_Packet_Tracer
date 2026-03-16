"""Topology intelligence tools — analyze, suggest, calculate addressing."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ....domain.models.plans import TopologyPlan
from ....domain.services.topology_analyzer import (
    analyze_topology,
    calculate_addressing,
    suggest_improvements,
)
from ....shared.logging import get_logger

logger = get_logger(__name__)


def register_topology_tools(mcp: FastMCP) -> None:
    """Register topology intelligence MCP tools."""

    @mcp.tool()
    def pt_analyze_topology(description: str) -> str:
        """
        Parse a natural language topology description into a structured analysis.

        Understands descriptions like:
        - "corporate network with 3 branches, web server and DMZ"
        - "red con 2 routers, 5 PCs, OSPF y DHCP"
        - "enterprise with HQ, 2 branches, redundancy"

        Returns JSON with sites, routing, subnets, and suggested device models.

        Parameters:
        - description: Natural language topology description
        """
        logger.info("pt_analyze_topology: %s", description[:80])
        result = analyze_topology(description)
        return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)

    @mcp.tool()
    def pt_suggest_improvements(plan_json: str) -> str:
        """
        Analyze an existing topology plan and suggest improvements.

        Checks for:
        - Missing redundancy (single uplinks, no backup paths)
        - Security gaps (flat network, no server isolation)
        - Connectivity issues (orphaned devices, missing routing)
        - Best practice violations (no DHCP, single-interface routers)

        Parameters:
        - plan_json: Plan JSON (output of pt_plan_topology)
        """
        logger.info("pt_suggest_improvements called")
        plan = TopologyPlan.model_validate_json(plan_json)
        improvements = suggest_improvements(plan)
        if not improvements:
            return json.dumps({
                "count": 0,
                "message": "No improvements suggested. Topology looks good!",
                "improvements": [],
            }, indent=2)
        return json.dumps({
            "count": len(improvements),
            "improvements": [imp.model_dump() for imp in improvements],
        }, indent=2, ensure_ascii=False)

    @mcp.tool()
    def pt_calculate_addressing(
        sites_json: str,
        vlans_json: str = "[]",
        enable_ipv6: bool = False,
    ) -> str:
        """
        Auto-generate a complete IP addressing plan for multiple sites.

        Assigns /24 per LAN, /30 per WAN link, /32 for loopbacks.
        Optionally includes IPv6 dual-stack addressing.

        Parameters:
        - sites_json: JSON array of sites, e.g.
          [{"name": "HQ", "routers": 2, "pcs": 10},
           {"name": "Branch1", "routers": 1, "pcs": 5}]
        - vlans_json: Optional JSON array of VLANs, e.g.
          [{"id": 10, "name": "SALES"}, {"id": 20, "name": "IT"}]
        - enable_ipv6: If true, includes IPv6 addresses (dual-stack)
        """
        logger.info("pt_calculate_addressing: ipv6=%s", enable_ipv6)
        sites = json.loads(sites_json)
        vlans = json.loads(vlans_json) if vlans_json else []
        result = calculate_addressing(sites, vlans, enable_ipv6=enable_ipv6)

        # Serialize AddressEntry models to dicts
        out: dict = {
            "devices": {},
            "summary": result.summary,
            "vlans": result.vlans,
        }
        for dev_name, ifaces in result.devices.items():
            out["devices"][dev_name] = {
                iface: entry.model_dump() for iface, entry in ifaces.items()
            }
        return json.dumps(out, indent=2, ensure_ascii=False)
