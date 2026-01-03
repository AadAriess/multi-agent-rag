"""
MCP Server untuk layanan tools dalam sistem Multi Agent RAG menggunakan FastMCP
"""
import logging
from typing import List
from mcp.server.fastmcp import FastMCP

# Inisialisasi Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inisialisasi FastMCP
# Nama ini akan muncul di client (seperti Claude Desktop atau host MCP lainnya)
mcp = FastMCP("Multi Agent RAG Server")
app = mcp
mcp_app = mcp

# --- REGISTRASI TOOLS ---

@mcp.tool()
async def search_local_documents(query: str) -> str:
    """
    Search for information in local compliance documents stored in Milvus.
    
    Args:
        query: Query to search for in local documents
    """
    from app.llms.agents.chatbot.specialist_agents import create_local_specialist_agent
    
    logger.info(f"Searching local documents for: {query}")
    agent = create_local_specialist_agent()
    # FastMCP menangani await jika fungsi mengembalikan coroutine
    return await agent.search_local_documents(query)

@mcp.tool()
async def search_internet(query: str) -> str:
    """
    Search for information on the internet using Searxng.
    
    Args:
        query: Query to search for on the internet
    """
    from app.llms.agents.chatbot.specialist_agents import create_search_specialist_agent
    
    logger.info(f"Searching internet for: {query}")
    agent = create_search_specialist_agent()
    return await agent.search_internet(query)

@mcp.tool()
async def store_search_memory(summary: str, search_id: str, session_id: str, source_urls: List[str]) -> str:
    """
    Store new search results in search_memory collection in Milvus.
    
    Args:
        summary: Summary of search results
        search_id: ID of the search
        session_id: Session ID
        source_urls: List of source URLs
    """
    from app.llms.agents.chatbot.memory_manager import memory_manager
    
    logger.info(f"Storing search memory for session: {session_id}")
    return await memory_manager.save_search_memory(summary, search_id, session_id, source_urls)

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# --- RUNNER ---

def run_mcp_sse_server():
    """Runner resmi untuk transport SSE"""
    print("🚀 Memulai FastMCP SSE Server...")
    try:
        mcp.settings.host = "0.0.0.0"  # Gunakan 0.0.0.0 agar bisa diakses dari network lain jika perlu
        mcp.settings.port = 8071       # Sesuaikan dengan config client Anda
        
        logger.info(f"🚀 Memulai FastMCP Server di http://{mcp.settings.host}:{mcp.settings.port}")
        mcp.run(transport="sse")
    except Exception as e:
        print(f"❌ Gagal menjalankan MCP Server: {e}")

if __name__ == "__main__":
    # Ini agar file tetap bisa dijalankan manual
    run_mcp_sse_server()