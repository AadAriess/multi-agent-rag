"""
Modul MCP (Model Context Protocol) untuk aplikasi OriensSpace AI
"""
from .mcp_client import mcp_client, initialize_mcp_client, get_mcp_client

__all__ = [
    "mcp_client",
    "initialize_mcp_client",
    "get_mcp_client"
]