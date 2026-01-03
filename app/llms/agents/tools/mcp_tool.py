"""
MCP Tool untuk integrasi dengan Model Context Protocol (Multi-Server Support)
"""
from app.llms.core.mcp.mcp_client import get_mcp_client
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

async def call_mcp_tool(tool_name: str, parameters: dict = None):
    """
    Fungsi untuk memanggil tool dari FastMCP Server (LMS/RAG)
    """
    client = await get_mcp_client()
    if client:
        # Menentukan server_name="lms" untuk FastMCP SSE
        return await client.acall(tool_name, parameters or {}, server_name="lms")
    else:
        logger.warning("MCP client (lms) not available")
        return None

async def call_sequential_thinking_tool(tool_name: str, parameters: dict = None):
    """
    Memanggil tool sequential thinking dengan deteksi nama tool otomatis.
    """
    client = await get_mcp_client()
    if not client:
        return None

    try:
        # 1. Ambil daftar tool asli dari server 'thinking'
        thinking_session = client.sessions.get("thinking")
        if not thinking_session:
            return None
            
        tools_resp = await thinking_session.list_tools()
        # Ambil nama tool pertama yang tersedia (biasanya cuma ada 1)
        actual_tool_name = tools_resp.tools[0].name 
        
        logger.info(f"🔍 [MCP_TOOL] Detected thinking tool name: {actual_tool_name}")

        # 2. Sesuaikan parameter agar cocok dengan skema server npx
        # Server npx mengharapkan 'thought', bukan 'input'
        final_params = {
            "thought": parameters.get("thought", parameters.get("input", "Analisis sistem")),
            "thoughtNumber": parameters.get("thoughtNumber", 1),
            "totalThoughts": parameters.get("totalThoughts", 1),
            "nextThoughtNeeded": parameters.get("nextThoughtNeeded", False)
        }

        # 3. Panggil dengan nama asli yang ditemukan
        result = await client.acall(actual_tool_name, final_params, server_name="thinking")
        
        if result and "result" in result:
            content_list = result["result"]
            if isinstance(content_list, list) and len(content_list) > 0:
                return {"result": content_list[0].text}
        return result

    except Exception as e:
        logger.error(f"❌ [MCP_TOOL] Error calling thinking tool: {e}")
        return {"error": str(e)}

async def list_mcp_tools(server: str = "lms"):
    """
    Mendapatkan daftar tool dari server tertentu
    """
    client = await get_mcp_client()
    if client and server in client.sessions:
        try:
            result = await client.sessions[server].list_tools()
            return result.tools
        except Exception as e:
            logger.error(f"Error listing tools for {server}: {e}")
            return []
    return []

def get_mcp_client_sync():
    """
    Fungsi sinkron untuk mendapatkan MCP client manager
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.create_task(get_mcp_client())
        else:
            return loop.run_until_complete(get_mcp_client())
    except Exception as e:
        logger.error(f"Error in get_mcp_client_sync: {e}")
        return None