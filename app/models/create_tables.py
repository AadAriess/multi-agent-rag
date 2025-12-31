"""
Script untuk membuat tabel-tabel di database MySQL
"""
from app.database.mysql_config import engine
from app.models.database_schema import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """Fungsi untuk membuat tabel-tabel di database"""
    logger.info("Membuat tabel-tabel di database MySQL...")
    
    try:
        # Buat semua tabel berdasarkan model
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tabel-tabel berhasil dibuat")
        
        # Verifikasi tabel telah dibuat
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"📊 Tabel-tabel yang ada di database: {tables}")
        
        # Verifikasi struktur tabel documents
        if 'documents' in tables:
            columns = inspector.get_columns('documents')
            logger.info("📋 Struktur tabel 'documents':")
            for col in columns:
                logger.info(f"   - {col['name']}: {col['type']} (nullable: {col['nullable']})")
        
        # Verifikasi struktur tabel contexts
        if 'contexts' in tables:
            columns = inspector.get_columns('contexts')
            logger.info("📋 Struktur tabel 'contexts':")
            for col in columns:
                logger.info(f"   - {col['name']}: {col['type']} (nullable: {col['nullable']})")
        
        # Verifikasi struktur tabel search_history
        if 'search_history' in tables:
            columns = inspector.get_columns('search_history')
            logger.info("📋 Struktur tabel 'search_history':")
            for col in columns:
                logger.info(f"   - {col['name']}: {col['type']} (nullable: {col['nullable']})")
                
    except Exception as e:
        logger.error(f"❌ Error saat membuat tabel: {e}")


def main():
    """Fungsi utama"""
    logger.info("Memulai pembuatan tabel-tabel database...")
    create_tables()
    logger.info("✅ Proses pembuatan tabel-tabel database selesai!")


if __name__ == "__main__":
    main()