"""Template tools — pt_list_config_templates, pt_apply_template."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ....domain.services.template_engine import list_available_templates, render_template
from ....shared.logging import get_logger

logger = get_logger(__name__)


def register_template_tools(mcp: FastMCP) -> None:
    """Register configuration template MCP tools."""

    @mcp.tool()
    def pt_list_config_templates() -> str:
        """
        List all available IOS configuration templates.

        Templates generate ready-to-paste IOS CLI commands for common
        configurations like OSPF, VLANs, HSRP, NAT, ACLs, DHCP, and STP.
        """
        logger.debug("pt_list_config_templates called")
        templates = list_available_templates()
        lines: list[str] = ["Available Configuration Templates:", ""]
        for name, desc in templates.items():
            lines.append(f"  **{name}** — {desc}")
        lines.append("")
        lines.append("Use pt_apply_template(template_name, context_json) to render.")
        return "\n".join(lines)

    @mcp.tool()
    def pt_apply_template(template_name: str, context_json: str) -> str:
        """
        Render an IOS configuration template with the given context.

        Returns ready-to-paste CLI commands for Packet Tracer.

        Template contexts:
        - ospf_basic: {process_id, router_id, networks: [{network, wildcard, area}],
          passive_interfaces: []}
        - eigrp_named: {name, as_number, router_id, networks: [{network, wildcard}],
          af: "ipv4"}
        - vlan_trunk: {vlans: [{id, name}], trunk_interfaces: [],
          access_ports: [{interface, vlan_id}]}
        - hsrp_pair: {interface, group, virtual_ip, priority, preempt, track_interface}
        - nat_overload: {inside_interface, outside_interface, acl_number,
          source_network, source_wildcard}
        - acl_dmz: {acl_name, rules: [{action, protocol, source, source_wildcard,
          destination, destination_wildcard, port}], interface, direction}
        - dhcp_server: {pools: [{name, network, mask, gateway, dns,
          excluded_start, excluded_end, lease_days}]}
        - stp_rapid: {mode, root_vlan, root_priority, portfast_interfaces: []}

        Parameters:
        - template_name: Template name (e.g. "ospf_basic", "nat_overload")
        - context_json: JSON object with template variables
        """
        logger.info("pt_apply_template: %s", template_name)
        context = json.loads(context_json)
        lines = render_template(template_name, context)
        return "\n".join(lines)
