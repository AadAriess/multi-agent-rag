"""
Modul untuk inisialisasi knowledge base
"""
import os
from app.llms.agents.chatbot.ingestion_pipeline import ingest_default_knowledge_base
from app.database.mysql_config import get_db
import logging

logger = logging.getLogger(__name__)


def initialize_knowledge_base():
    """
    Fungsi untuk menginisialisasi knowledge base dari direktori data/knowledge_base/
    """
    logger.info("Memulai inisialisasi knowledge base...")
    
    # Dapatkan session database
    db = next(get_db())
    
    try:
        # Lakukan ingestion dari direktori default
        success = ingest_default_knowledge_base(db)
        
        if success:
            logger.info("Knowledge base berhasil diinisialisasi")
        else:
            logger.error("Gagal menginisialisasi knowledge base")
    except Exception as e:
        logger.error(f"Error saat inisialisasi knowledge base: {e}")
    finally:
        # Tutup session database
        db.close()


# Panggil fungsi inisialisasi jika file ini dijalankan langsung
if __name__ == "__main__":
    initialize_knowledge_base()