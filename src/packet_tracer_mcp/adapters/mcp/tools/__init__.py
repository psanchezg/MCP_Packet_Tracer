"""MCP tool modules — split by domain concern."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .bridge_tools import register_bridge_tools
from .catalog_tools import register_catalog_tools
from .deploy_tools import register_deploy_tools
from .generation_tools import register_generation_tools
from .planning_tools import register_planning_tools
from .preset_tools import register_preset_tools
from .template_tools import register_template_tools
from .topology_tools import register_topology_tools
from .validation_tools import register_validation_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register every MCP tool on *mcp*."""
    register_catalog_tools(mcp)
    register_planning_tools(mcp)
    register_validation_tools(mcp)
    register_generation_tools(mcp)
    register_deploy_tools(mcp)
    register_bridge_tools(mcp)
    register_topology_tools(mcp)
    register_preset_tools(mcp)
    register_template_tools(mcp)
