"""
MCP Server untuk layanan tools dalam sistem Multi Agent RAG
"""
import asyncio
import json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class MCPTool(BaseModel):
    """
    Model untuk definisi tool MCP
    """
    name: str
    description: str
    parameters: Dict[str, Any] = {}


class MCPServer:
    """
    Server MCP untuk menyediakan akses tool ke LLM
    """

    def __init__(self):
        self.tools: Dict[str, callable] = {}
        self.capabilities = {
            "tools": [],
            "prompts": [],
            "resources": []
        }

    def register_tool(self, name: str, func, description: str = "", parameters: Dict[str, Any] = None):
        """Mendaftarkan tool baru ke MCP server"""
        self.tools[name] = {
            "function": func,
            "description": description,
            "parameters": parameters or {}
        }
        self.capabilities["tools"].append({
            "name": name,
            "description": description,
            "parameters": parameters or {}
        })

    async def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Menangani permintaan MCP"""
        try:
            if method == "tools/list":
                return {"result": self.capabilities["tools"]}
            elif method.startswith("tools/call/"):
                tool_name = method.split("/")[-1]
                if tool_name in self.tools:
                    result = self.tools[tool_name]["function"](**params)
                    # Jika fungsi mengembalikan coroutine, jalankan sebagai async
                    if asyncio.iscoroutine(result):
                        result = await result
                    return {"result": result}
                else:
                    return {"error": f"Tool {tool_name} not found"}
            else:
                return {"error": f"Method {method} not supported"}
        except Exception as e:
            logger.error(f"Error handling MCP request: {str(e)}")
            return {"error": str(e)}

    def get_tool_list(self) -> List[Dict[str, Any]]:
        """Mendapatkan daftar tool yang terdaftar"""
        return self.capabilities["tools"]


# Global instance
mcp_server = MCPServer()


def register_mcp_tools():
    """
    Fungsi untuk mendaftarkan semua tool yang diperlukan ke MCP server
    """
    # Import setelah inisialisasi untuk menghindari circular import
    from app.llms.agents.chatbot.specialist_agents import create_local_specialist_agent, create_search_specialist_agent

    # Mendaftarkan fungsi untuk pencarian di Milvus
    def search_local_documents(query: str):
        agent = create_local_specialist_agent()
        return agent.search_local_documents(query)

    # Mendaftarkan fungsi untuk pencarian di internet
    def search_internet(query: str):
        agent = create_search_specialist_agent()
        return agent.search_internet(query)

    # Mendaftarkan fungsi untuk menyimpan ke memori pencarian
    def store_search_memory(summary: str, search_id: str, session_id: str, source_urls: List[str]):
        from app.llms.agents.chatbot.memory_manager import memory_manager
        return memory_manager.save_search_memory(summary, search_id, session_id, source_urls)

    # Daftarkan tool ke MCP server
    mcp_server.register_tool(
        "search_local_documents",
        search_local_documents,
        "Search for information in local compliance documents stored in Milvus",
        {"query": {"type": "string", "description": "Query to search for in local documents"}}
    )

    mcp_server.register_tool(
        "search_internet",
        search_internet,
        "Search for information on the internet using Searxng",
        {"query": {"type": "string", "description": "Query to search for on the internet"}}
    )

    mcp_server.register_tool(
        "store_search_memory",
        store_search_memory,
        "Store new search results in search_memory collection in Milvus",
        {
            "summary": {"type": "string", "description": "Summary of search results"},
            "search_id": {"type": "string", "description": "ID of the search"},
            "session_id": {"type": "string", "description": "Session ID"},
            "source_urls": {"type": "array", "items": {"type": "string"}, "description": "List of source URLs"}
        }
    )

    logger.info("MCP tools registered successfully")


# FastAPI app untuk MCP server
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Registrasi tools saat startup
    register_mcp_tools()
    yield


app = FastAPI(
    title="MCP Server for Multi Agent RAG",
    description="Model Context Protocol server untuk menyediakan akses tool ke LLM",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Endpoint untuk mengecek kesehatan server MCP"""
    return {"status": "healthy", "service": "MCP Server"}


@app.get("/tools")
async def list_tools():
    """Endpoint untuk mendapatkan daftar tool yang tersedia"""
    return {"tools": mcp_server.get_tool_list()}


@app.post("/call")
async def call_tool(request: Dict[str, Any]):
    """Endpoint untuk memanggil tool MCP"""
    method = request.get("method")
    params = request.get("params", {})

    if not method:
        raise HTTPException(status_code=400, detail="Method is required")

    result = await mcp_server.handle_request(method, params)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


if __name__ == "__main__":
    import uvicorn
    # Gunakan port yang sesuai dengan konfigurasi di settings
    uvicorn.run(app, host="0.0.0.0", port=8071)  # Gunakan port 8071 sesuai konfigurasi default