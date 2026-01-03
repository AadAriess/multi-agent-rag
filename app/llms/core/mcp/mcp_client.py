"""
MCP Client menggunakan SDK resmi untuk berkomunikasi dengan Multi-Server (FastMCP & Sequential Thinking)
"""
import asyncio
import logging
import shutil
from typing import Dict, Any, Optional, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from app.core.config import settings

logger = logging.getLogger(__name__)

class MultiMCPClient:
    """
    Client resmi yang mengelola koneksi ke beberapa MCP Server:
    1. lms: FastMCP Server berbasis SSE (Port 8071)
    2. thinking: Sequential Thinking Server berbasis STDIO (npx)
    """

    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self.connected = False
        self.mcp_url = "http://localhost:8071/sse"

    async def connect(self) -> bool:
        """
        Membuat koneksi ke semua server MCP
        """
        try:
            # --- 1. Koneksi ke FastMCP Server (SSE) ---
            try:
                sse_streams = await self._exit_stack.enter_async_context(sse_client(url=self.mcp_url))
                self.sessions["lms"] = await self._exit_stack.enter_async_context(
                    ClientSession(sse_streams[0], sse_streams[1])
                )
                await self.sessions["lms"].initialize()
                logger.info(f"✅ Connected to FastMCP SSE: {self.mcp_url}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to FastMCP SSE: {e}")

            # --- 2. Koneksi ke Sequential Thinking (STDIO via npx) ---
            try:
                npx_path = shutil.which("npx")
                if not npx_path:
                    raise RuntimeError("npx not found in system PATH")

                server_params = StdioServerParameters(
                    command=npx_path,
                    args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
                    env=None
                )
                
                stdio_streams = await self._exit_stack.enter_async_context(stdio_client(server_params))
                self.sessions["thinking"] = await self._exit_stack.enter_async_context(
                    ClientSession(stdio_streams[0], stdio_streams[1])
                )
                await self.sessions["thinking"].initialize()
                logger.info("✅ Connected to Sequential Thinking Server (npx)")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Thinking Server: {e}")

            self.connected = len(self.sessions) > 0
            return self.connected
            
        except Exception as e:
            logger.error(f"❌ Critical failure in MultiMCPClient connect: {e}")
            return False

    async def disconnect(self):
        await self._exit_stack.aclose()
        self.connected = False
        self.sessions = {}
        logger.info("Disconnected from all MCP servers")

    def is_available(self, server_name: str = "lms") -> bool:
        return server_name in self.sessions

    async def acall(self, tool_name: str, parameters: Dict[str, Any] = None, server_name: str = "lms") -> Optional[Dict[str, Any]]:
        """
        Memanggil tool dari server tertentu (default: lms)
        """
        if not self.is_available(server_name):
            logger.warning(f"Server {server_name} not available, reconnecting...")
            if not await self.connect():
                return None

        try:
            session = self.sessions[server_name]
            result = await session.call_tool(tool_name, arguments=parameters or {})
            return {"result": result.content}
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            return {"error": str(e)}

# --- Global Instance Management ---

mcp_client = None 

async def initialize_mcp_client():
    global mcp_client
    if mcp_client is None:
        mcp_client = MultiMCPClient()
        await mcp_client.connect()
    return mcp_client

async def get_mcp_client() -> Optional[MultiMCPClient]:
    global mcp_client
    if mcp_client is None:
        await initialize_mcp_client()
    return mcp_client

def sync_initialize_mcp_client():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.create_task(initialize_mcp_client())
        else:
            return loop.run_until_complete(initialize_mcp_client())
    except Exception as e:
        logger.error(f"Error in sync_initialize_mcp_client: {e}")
        return None