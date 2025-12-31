"""
File utama aplikasi OriensSpace AI
"""
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import config, settings
from app.llms.core.mcp.mcp_client import sync_initialize_mcp_client
from app.llms.core import run_mcp_server_in_background


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Jalankan MCP server di background
    run_mcp_server_in_background()
    # Tunggu sebentar agar MCP server siap sebelum inisialisasi client
    time.sleep(3)
    # Initialize MCP client
    sync_initialize_mcp_client()
    yield


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