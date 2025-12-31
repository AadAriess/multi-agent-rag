"""
File untuk menjalankan aplikasi OriensSpace AI
"""
import uvicorn
from app.main import app
from app.core.config import config
from app.core.config import settings
from app.core.logging import setup_logging


def main():
    """Fungsi utama untuk menjalankan aplikasi"""
    # Setup logging
    setup_logging()

    # Jalankan aplikasi
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()