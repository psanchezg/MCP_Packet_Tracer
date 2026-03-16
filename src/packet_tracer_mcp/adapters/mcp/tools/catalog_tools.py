"""Catalog query tools: pt_list_devices, pt_list_templates, pt_get_device_details."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ....infrastructure.catalog.aliases import MODEL_ALIASES
from ....infrastructure.catalog.devices import ALL_MODELS
from ....infrastructure.catalog.templates import list_templates
from ....shared.logging import get_logger

logger = get_logger(__name__)


def register_catalog_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def pt_list_devices() -> str:
        """
        List all available Packet Tracer devices with their ports.
        Use this to discover which models, ports, and cables you can use.
        """
        logger.debug("pt_list_devices called")
        lines: list[str] = []
        for name, model in ALL_MODELS.items():
            ports = ", ".join(port.full_name for port in model.ports) or "(none)"
            lines.append(f"**{model.display_name}** (type: `{name}`, category: {model.category})")
            lines.append(f"  Ports: {ports}")
            lines.append("")
        lines.append("**Available aliases:**")
        for alias, target in MODEL_ALIASES.items():
            lines.append(f"  {alias} -> {target}")
        return "\n".join(lines)

    @mcp.tool()
    def pt_list_templates() -> str:
        """
        List all available topology templates with descriptions.
        """
        logger.debug("pt_list_templates called")
        templates = list_templates()
        lines: list[str] = []
        for template in templates:
            lines.append(f"**{template.name}** (key: `{template.key.value}`)")
            lines.append(f"  {template.description}")
            lines.append(
                f"  Routers: {template.min_routers}-{template.max_routers} "
                f"(default: {template.default_routers})"
            )
            lines.append(
                f"  PCs/LAN: {template.default_pcs_per_lan}  |  "
                f"WAN: {'yes' if template.requires_wan else 'no'}"
            )
            lines.append(f"  Routing: {template.default_routing.value}")
            lines.append(f"  Tags: {', '.join(template.tags)}")
            lines.append("")
        return "\n".join(lines)

    @mcp.tool()
    def pt_get_device_details(model_name: str) -> str:
        """
        Show details of a specific device model.

        Parameters:
        - model_name: model name (e.g. '2911', '2960', 'PC')
        """
        logger.debug("pt_get_device_details: %s", model_name)
        model = ALL_MODELS.get(model_name)
        if not model:
            return f"Model '{model_name}' not found. Use pt_list_devices to see available models."

        info = {
            "display_name": model.display_name,
            "category": model.category,
            "ports": [
                {
                    "name": port.full_name,
                    "speed": port.speed.value if hasattr(port.speed, "value") else port.speed,
                }
                for port in model.ports
            ],
            "total_ports": len(model.ports),
        }
        return json.dumps(info, indent=2, ensure_ascii=False)
