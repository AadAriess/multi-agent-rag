"""
Inisialisasi sistem Multi Agent RAG untuk aplikasi OriensSpace AI
"""
import subprocess
import json
import threading
from app.database.milvus_config import connect_to_milvus, create_milvus_collections
import logging

logger = logging.getLogger(__name__)


def run_sequential_thinking_server():
    """
    Fungsi untuk menjalankan server sequential-thinking sesuai konfigurasi di mcp.json
    """
    def start_sequential_thinking_server():
        try:
            # Baca konfigurasi dari mcp.json
            with open('mcp.json', 'r') as f:
                config = json.load(f)

            server_config = config.get('mcpServers', {}).get('sequential-thinking', {})

            if server_config.get('command') == 'npx' and server_config.get('args'):
                # Jalankan server sequential-thinking menggunakan npx
                cmd = ['npx'] + server_config['args']
                subprocess.run(cmd, check=True)
            else:
                logger.warning("Konfigurasi server sequential-thinking tidak ditemukan atau tidak valid di mcp.json")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error saat menjalankan server sequential-thinking: {e}")
        except FileNotFoundError:
            logger.error("npx tidak ditemukan. Pastikan Node.js dan npm telah diinstal.")
        except Exception as e:
            logger.error(f"Error saat menjalankan server sequential-thinking: {e}")

    # Jalankan server sequential-thinking di thread terpisah
    seq_thread = threading.Thread(target=start_sequential_thinking_server, daemon=True)
    seq_thread.start()
    print("Server sequential-thinking dimulai di background thread")


def initialize_multi_agent_rag_system():
    """
    Fungsi untuk menginisialisasi seluruh sistem Multi Agent RAG
    """
    print("Memulai inisialisasi sistem Multi Agent RAG...")

    # Inisialisasi koneksi Milvus
    print("Menginisialisasi koneksi Milvus...")
    connect_to_milvus()
    compliance_docs_collection, search_memory_collection = create_milvus_collections()
    print("Koneksi Milvus berhasil diinisialisasi")

    print("Sistem Multi Agent RAG siap digunakan")

    return {
        "compliance_docs_collection": compliance_docs_collection,
        "search_memory_collection": search_memory_collection
    }


# Inisialisasi sistem
multi_agent_rag_system = initialize_multi_agent_rag_system()

print("Semua komponen Multi Agent RAG telah diinisialisasi")