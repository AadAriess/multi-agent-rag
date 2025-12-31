#!/usr/bin/env python3
"""
Script untuk membersihkan semua record dari tabel Milvus dan menjalankan ingestion ulang
"""
import sys
import os
from pathlib import Path

# Tambahkan path root proyek ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.milvus_config import connect_to_milvus, milvus_collection
from pymilvus import utility, Collection
from app.llms.agents.chatbot.ingestion_pipeline import ingest_default_knowledge_base
from app.database.mysql_config import get_db
import logging

# Aktifkan logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_milvus_collection():
    """Hapus semua record dari koleksi Milvus"""
    try:
        # Cek apakah koleksi ada
        if not utility.has_collection(milvus_collection.name):
            logger.warning(f"Collection {milvus_collection.name} does not exist")
            return False

        # Dapatkan koleksi
        collection = Collection(milvus_collection.name)
        
        # Hitung jumlah entitas sebelum dihapus
        collection.load()  # Load collection sebelum menghitung
        initial_count = collection.num_entities
        logger.info(f"Initial count in Milvus: {initial_count}")
        
        # Hapus semua entitas
        collection.drop()
        logger.info("All records have been deleted from Milvus collection")
        
        # Kita perlu recreate collection karena Milvus tidak punya fungsi truncate
        from app.database.milvus_config import create_milvus_collections
        create_milvus_collections()
        logger.info("Milvus collection recreated")
        
        return True
    except Exception as e:
        logger.error(f"Error clearing Milvus collection: {str(e)}")
        return False


def main():
    """Main function untuk membersihkan Milvus dan menjalankan ingestion"""
    print("=== Clear Milvus and Re-ingest Documents ===")
    
    # Connect ke Milvus
    connect_to_milvus()
    logger.info("Connected to Milvus")
    
    # Hapus semua record dari Milvus
    if clear_milvus_collection():
        logger.info("Successfully cleared Milvus collection")
    else:
        logger.error("Failed to clear Milvus collection")
        return False


if __name__ == "__main__":
    main()