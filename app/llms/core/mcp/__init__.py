"""
Modul MCP (Model Context Protocol) untuk aplikasi OriensSpace AI
"""
from .mcp_client import mcp_client, initialize_mcp_client, get_mcp_client
from .mcp_server import mcp_server, register_mcp_tools, app as mcp_app

__all__ = [
    "mcp_client",
    "initialize_mcp_client",
    "get_mcp_client",
    "mcp_server",
    "register_mcp_tools",
    "mcp_app"
]