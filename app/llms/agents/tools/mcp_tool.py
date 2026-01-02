"""
MCP Tool untuk integrasi dengan Model Context Protocol
"""
from app.llms.core.mcp.mcp_client import get_mcp_client, mcp_client, sync_initialize_mcp_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Inisialisasi MCP client
try:
    sync_initialize_mcp_client()
except Exception as e:
    logger.error(f"Error initializing MCP client: {e}")
    mcp_client = None


async def call_mcp_tool(tool_name: str, parameters: dict = None):
    """
    Fungsi untuk memanggil tool MCP
    """
    client = await get_mcp_client()
    if client:
        return await client.acall(tool_name, parameters or {})
    else:
        logger.warning("MCP client not available")
        return None


async def list_mcp_tools(server_name: str = "lms"):
    """
    Fungsi untuk mendapatkan daftar tool MCP
    """
    client = await get_mcp_client()
    if client:
        return await client.list_tools(server_name)
    else:
        logger.warning("MCP client not available")
        return None


async def call_sequential_thinking_tool(tool_name: str, parameters: dict = None):
    """
    Fungsi untuk memanggil tool dari server sequential-thinking
    """
    logger.info(f"[MCP_TOOL] Attempting to call sequential-thinking tool: {tool_name}")

    client = await get_mcp_client()
    if client:
        logger.info(f"[MCP_TOOL] MCP client is available, attempting to call: sequential-thinking:{tool_name}")

        # Gunakan format "server_name:tool_name" untuk memanggil tool dari server tertentu
        full_tool_name = f"sequential-thinking:{tool_name}"
        try:
            result = await client.acall(full_tool_name, parameters or {})
            logger.info(f"[MCP_TOOL] Successfully called {full_tool_name}, result: {result}")
            return result
        except Exception as e:
            logger.error(f"[MCP_TOOL] Error calling {full_tool_name}: {e}")

            # Coba panggil tool tanpa prefix server jika gagal
            try:
                logger.info(f"[MCP_TOOL] Trying to call {tool_name} without server prefix")
                result = await client.acall(tool_name, parameters or {})
                logger.info(f"[MCP_TOOL] Successfully called {tool_name} without prefix, result: {result}")
                return result
            except Exception as e2:
                logger.error(f"[MCP_TOOL] Error calling {tool_name} without prefix: {e2}")
                return None
    else:
        logger.warning("[MCP_TOOL] MCP client not available")
        return None


# Fungsi untuk kompatibilitas dengan kode lama
def get_mcp_client_sync():
    """
    Fungsi sinkron untuk mendapatkan MCP client (untuk kompatibilitas)
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # Jika ada event loop, kita tidak bisa menggunakan run_until_complete
        # Jadi kita kembalikan coroutine yang bisa diawait
        async def get_client():
            return await get_mcp_client()
        return get_client()
    except RuntimeError:
        # Tidak ada event loop yang berjalan
        return asyncio.run(get_mcp_client())