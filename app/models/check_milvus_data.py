#!/usr/bin/env python3
"""
Script untuk memeriksa data di Milvus
"""
import sys
import os

# Tambahkan path root proyek ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.milvus_config import connect_to_milvus, milvus_collection
from pymilvus import Collection
import logging

# Aktifkan logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_milvus_data():
    """Cek data di Milvus"""
    try:
        # Connect ke Milvus
        connect_to_milvus()
        logger.info("Connected to Milvus")
        
        # Dapatkan koleksi
        collection = Collection(milvus_collection.name)
        
        # Load collection untuk menghitung entitas
        collection.load()
        
        # Hitung jumlah entitas
        count = collection.num_entities
        logger.info(f"Total entities in Milvus: {count}")
        
        # Query beberapa entitas untuk verifikasi
        if count > 0:
            # Ambil 5 entitas pertama sebagai sampel
            results = collection.query(
                expr="0 <= id < 5",  # Ambil entitas dengan ID 0-4 sebagai contoh
                output_fields=["text", "metadata"]
            )
            
            logger.info(f"Sample of {len(results)} entities:")
            for i, result in enumerate(results):
                logger.info(f"Entity {i}: ID={result['id']}, Metadata={result['metadata']}")
                logger.info(f"Text snippet: {result['text'][:100]}...")
        
        # Release collection
        collection.release()
        
        return count
        
    except Exception as e:
        logger.error(f"Error checking Milvus data: {str(e)}")
        return 0


def main():
    """Main function"""
    print("=== Check Milvus Data ===")
    entity_count = check_milvus_data()
    print(f"Total entities in Milvus: {entity_count}")


if __name__ == "__main__":
    main()