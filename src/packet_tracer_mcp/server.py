"""
MCP Server for Packet Tracer.

Entry point: creates the server, registers tools/resources, and starts
on streamable-http (:39000) or stdio depending on the --stdio flag.
"""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

from .adapters.mcp.resource_registry import register_resources
from .adapters.mcp.tool_registry import register_tools
from .settings import SERVER_INSTRUCTIONS, SERVER_NAME
from .shared.logging import configure_logging, get_logger

TRANSPORT_PORT = int(os.environ.get("PT_MCP_PORT", "39000"))

mcp = FastMCP(
    SERVER_NAME,
    instructions=SERVER_INSTRUCTIONS,
    host="127.0.0.1",
    port=TRANSPORT_PORT,
    stateless_http=True,
)

register_tools(mcp)
register_resources(mcp)


def main():
    """Start the MCP server.

    Default: streamable-http on the configured port.
    With --stdio: uses stdio transport (for debug or legacy clients).
    """
    configure_logging()
    logger = get_logger(__name__)

    if "--stdio" in sys.argv:
        logger.info("Starting MCP server (stdio transport)")
        mcp.run(transport="stdio")
    else:
        logger.info("Starting MCP server on http://127.0.0.1:%d/mcp", TRANSPORT_PORT)
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
