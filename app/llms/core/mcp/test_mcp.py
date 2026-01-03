import asyncio
import logging
from app.llms.core.mcp.mcp_client import get_mcp_client
from app.llms.agents.tools.mcp_tool import call_mcp_tool, call_sequential_thinking_tool

# Atur logging agar kita bisa melihat proses koneksi di terminal
logging.basicConfig(level=logging.INFO)

async def test_multi_server_mcp():
    print("🚀 Memulai Test Multi-Server MCP...")
    
    try:
        # 1. Test Server 1: FastMCP (LMS/RAG) di port 8071
        print("\n--- 🧪 Test 1: FastMCP Server (LMS) ---")
        result_add = await call_mcp_tool("add", {"a": 15, "b": 15})
        print(f"✅ Hasil Tool 'add' (Expect 30): {result_add}")

        result_search = await call_mcp_tool("search_internet", {"query": "AI News 2026"})
        if result_search and "result" in result_search:
            print(f"✅ Hasil 'search_internet' berhasil didapatkan.")
            # Print potongan hasil agar tidak memenuhi layar
            print(f"Preview: {str(result_search['result'])[0:200]}...")
        else:
            print(f"❌ Gagal memanggil search_internet: {result_search}")

        # 2. Test Server 2: Sequential Thinking (via npx)
        print("\n--- 🧪 Test 2: Sequential Thinking Server (npx) ---")
        thought_params = {
            "thought": "Saya perlu memverifikasi apakah kedua server MCP ini terhubung dengan benar untuk sistem RAG.",
            "thoughtNumber": 1,
            "totalThoughts": 1,
            "nextThoughtNeeded": False
        }
        
        # Nama tool 'sequentialThinking' sesuai dengan dokumentasi resmi server npx tersebut
        result_think = await call_sequential_thinking_tool("sequentialThinking", thought_params)
        
        if result_think:
            print(f"✅ Hasil 'sequentialThinking' berhasil!")
            print(f"Output: {result_think}")
        else:
            print("❌ Gagal memanggil Sequential Thinking server.")

    except Exception as e:
        print(f"❌ Terjadi kesalahan fatal: {e}")
    finally:
        # Menutup koneksi secara bersih
        client = await get_mcp_client()
        if client:
            await asyncio.sleep(0.2)
            await client.disconnect()
            print("\n🔌 Koneksi ditutup.")

if __name__ == "__main__":
    asyncio.run(test_multi_server_mcp())