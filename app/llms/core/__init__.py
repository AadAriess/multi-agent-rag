"""
File inisialisasi untuk sistem Multi Agent RAG
"""
import threading
import uvicorn
from app.llms.core.mcp.mcp_server import app as mcp_app
from app.database.milvus_config import connect_to_milvus, create_milvus_collections
from app.llms.agents.chatbot.knowledge_base_initializer import initialize_knowledge_base
import logging

logger = logging.getLogger(__name__)


def initialize_multi_agent_rag():
    """
    Fungsi untuk menginisialisasi seluruh sistem Multi Agent RAG
    """
    print("Memulai inisialisasi sistem Multi Agent RAG...")

    # Inisialisasi koneksi Milvus
    print("Menginisialisasi koneksi Milvus...")
    connect_to_milvus()
    compliance_docs_collection, search_memory_collection = create_milvus_collections()
    print("Koneksi Milvus berhasil diinisialisasi")

    # Inisialisasi knowledge base
    print("Menginisialisasi knowledge base...")
    initialize_knowledge_base()
    print("Knowledge base berhasil diinisialisasi")

    print("Sistem Multi Agent RAG siap digunakan")

    return {
        "compliance_docs_collection": compliance_docs_collection,
        "search_memory_collection": search_memory_collection
    }


def run_mcp_server_in_background():
    """
    Fungsi untuk menjalankan MCP server di background thread
    """
    def start_server():
        try:
            uvicorn.run(
                mcp_app,
                host="0.0.0.0",
                port=8071,
                log_level="info"
            )
        except Exception as e:
            logger.error(f"Error saat menjalankan MCP server: {e}")

    # Jalankan MCP server di thread terpisah
    mcp_thread = threading.Thread(target=start_server, daemon=True)
    mcp_thread.start()
    print("MCP server dimulai di background thread")


# Inisialisasi sistem
multi_agent_rag_system = initialize_multi_agent_rag()

print("Semua komponen Multi Agent RAG telah diinisialisasi")