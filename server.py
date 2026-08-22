# Copyright (c) 2026 bachbnt. All rights reserved.
#
# MCP server configuration (add to ~/.claude/settings.json):
# {
#   "mcpServers": {
#     "finhub": {
#       "command": "/Users/bachbui/Desktop/source/finhub-mcp/.venv/bin/python",
#       "args": ["/Users/bachbui/Desktop/source/finhub-mcp/server.py"]
#     }
#   }
# }

from mcp.server.fastmcp import FastMCP

from finhub_mcp.tools import alerts, crypto, market, vn_stock


def create_mcp() -> FastMCP:
    """Create and register the FinHub MCP server."""
    mcp = FastMCP("finhub-mcp")
    vn_stock.register(mcp)
    crypto.register(mcp)
    market.register(mcp)
    alerts.register(mcp)
    return mcp


mcp = create_mcp()


def main() -> None:
    mcp.run()


if __name__ == '__main__':
    main()
