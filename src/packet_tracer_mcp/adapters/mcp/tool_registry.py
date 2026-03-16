"""
MCP Tool Registry — thin coordinator.

Delegates to focused modules under tools/.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .tools import register_all_tools


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools on the server (backwards-compatible entry point)."""
    register_all_tools(mcp)
