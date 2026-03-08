"""
Servidor MCP para Packet Tracer — V2.

Punto de entrada delgado: crea el servidor, registra tools y resources.
"""

from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from .settings import SERVER_NAME, SERVER_INSTRUCTIONS
from .adapters.mcp.tool_registry import register_tools
from .adapters.mcp.resource_registry import register_resources

mcp = FastMCP(
    SERVER_NAME,
    instructions=SERVER_INSTRUCTIONS,
)

register_tools(mcp)
register_resources(mcp)


def main():
    """Arranca el servidor MCP por stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
