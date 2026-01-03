"""
File utama aplikasi OriensSpace AI
"""
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

from app.core.config import config, settings
from app.llms.core.mcp.mcp_client import get_mcp_client, sync_initialize_mcp_client
from app.llms.core import run_mcp_server_in_background

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Mengelola lifecycle aplikasi:
    1. Menjalankan Server MCP (FastMCP SSE + npx thinking)
    2. Menghubungkan Client ke server-server tersebut
    3. Cleanup saat aplikasi dimatikan
    """
    try:
        # Menjalankan MCP server di background
        logger.info("Initializing MCP Infrastructure...")
        run_mcp_server_in_background()
        
        # Jeda asinkron (tidak memblokir request lain)
        await asyncio.sleep(3)
        
        # Initialize MCP client ganda
        sync_initialize_mcp_client()
        logger.info("OriensSpace AI Components Ready.")
        
        yield
    finally:
        # Cleanup: Tutup koneksi agar tidak ada process npx yang menggantung
        logger.info("Shutting down OriensSpace AI...")
        client = await get_mcp_client()
        if client:
            # Menggunakan loop asinkron untuk menutup client
            try:
                # Jika dalam konteks shutdown, kita bisa paksa tutup
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(client.disconnect())
            except Exception as e:
                logger.error(f"Shutdown error: {e}")


app = FastAPI(
    title=config.PROJECT_NAME,
    debug=config.DEBUG,
    lifespan=lifespan
)

# Konfigurasi CORS
cors_origins = config.CORS_ORIGINS
origins = [origin.strip() for origin in cors_origins.split(",")] if cors_origins else ["*"]

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import router setelah inisialisasi app untuk menghindari circular import
from app.api.v1.routers import index

# Registrasi router
app.include_router(index.router, prefix=config.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": "Welcome to OriensSpace AI API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )