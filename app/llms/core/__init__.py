"""
File inisialisasi untuk sistem Multi Agent RAG
"""
import threading
import logging
import asyncio
from typing import Dict, Any
import multiprocessing

logger = logging.getLogger(__name__)

# Variabel global untuk menyimpan status sistem
_rag_system_cache = None

def initialize_multi_agent_rag() -> Dict[str, Any]:
    """
    Fungsi untuk menginisialisasi seluruh sistem Multi Agent RAG.
    Menggunakan caching agar tidak terjadi inisialisasi ganda.
    """
    global _rag_system_cache
    if _rag_system_cache:
        return _rag_system_cache

    print("🚀 Memulai inisialisasi sistem Multi Agent RAG...")

    try:
        from app.database.milvus_config import connect_to_milvus, create_milvus_collections
        from app.llms.agents.chatbot.knowledge_base_initializer import initialize_knowledge_base

        # 1. Inisialisasi koneksi Milvus
        print("📦 Menginisialisasi koneksi Milvus...")
        connect_to_milvus()
        compliance_docs, search_memory = create_milvus_collections()
        print("✅ Koneksi Milvus berhasil")

        # 2. Inisialisasi knowledge base (Ingestion)
        print("📚 Menginisialisasi knowledge base...")
        initialize_knowledge_base()
        print("✅ Knowledge base siap")

        _rag_system_cache = {
            "compliance_docs_collection": compliance_docs,
            "search_memory_collection": search_memory
        }
        
        print("✨ Sistem Multi Agent RAG siap digunakan")
        return _rag_system_cache

    except Exception as e:
        logger.error(f"❌ Gagal menginisialisasi RAG System: {e}")
        # Kembalikan struktur kosong agar aplikasi tidak crash total
        return {"compliance_docs_collection": None, "search_memory_collection": None}


def run_mcp_server_in_background():
    """
    Menjalankan runner FastMCP di Process terpisah.
    Ini identik dengan menjalankan 'python mcp_server.py' di terminal lain.
    """
    def start_server_process():
        try:
            # Import di dalam fungsi untuk menghindari circular import
            from app.llms.core.mcp.mcp_server import run_mcp_sse_server
            run_mcp_sse_server()
        except Exception as e:
            logger.error(f"❌ Error di dalam MCP Process: {e}")

    # Menggunakan Process (bukan Thread) agar Event Loop tidak tabrakan
    p = multiprocessing.Process(target=start_server_process, daemon=True)
    p.start()
    
    print(f"📡 MCP Server Process started (PID: {p.pid}) on Port 8071")


# JANGAN jalankan inisialisasi otomatis di level modul jika ingin control penuh di main.py
# Namun, jika Anda ingin tetap otomatis, biarkan seperti di bawah ini:
# multi_agent_rag_system = initialize_multi_agent_rag()