"""
MCP Client untuk komunikasi dengan server MCP
"""
import asyncio
import json
from typing import Dict, Any, Optional
import aiohttp
from app.core.config import settings
import logging
import time

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client untuk berkomunikasi dengan Model Context Protocol (MCP) server
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        self.mcp_url = settings.mcp_server_url if hasattr(settings, 'mcp_server_url') else "http://localhost:8071/sse"

        # Baca konfigurasi dari mcp.json untuk mendapatkan semua server MCP
        try:
            with open('mcp.json', 'r') as f:
                config = json.load(f)
            self.mcp_servers = config.get('mcpServers', {})
        except Exception as e:
            logger.warning(f"Error membaca mcp.json: {e}, menggunakan konfigurasi default")
            self.mcp_servers = {}

    async def connect(self) -> bool:
        """
        Membuat koneksi ke MCP server
        """
        for attempt in range(self.max_retries):
            try:
                self.session = aiohttp.ClientSession()
                # Lakukan ping ke server untuk memastikan koneksi
                async with self.session.get(f"{self.mcp_url.replace('/sse', '')}/health") as resp:
                    if resp.status == 200:
                        self.connected = True
                        logger.info("✅ MCP server connected successfully")
                        return True
            except Exception as e:
                logger.warning(f"MCP server connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                if self.session:
                    await self.session.close()
                    self.session = None
        logger.warning("MCP server connection failed after all retries, continuing without MCP tools")
        self.connected = False
        return False

    async def disconnect(self):
        """
        Memutus koneksi dari MCP server
        """
        if self.session:
            await self.session.close()
            self.session = None
            self.connected = False

    def is_available(self) -> bool:
        """
        Memeriksa apakah MCP client tersedia dan terhubung
        """
        return self.connected and self.session is not None

    async def acall(self, tool_name: str, parameters: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Memanggil tool MCP secara async
        """
        if not self.is_available():
            logger.warning("MCP client not available")
            return None

        parameters = parameters or {}

        # Cek apakah tool_name mengandung nama server (misalnya "sequential-thinking:tool_name")
        server_name = "lms"  # Default server
        actual_tool_name = tool_name

        if ":" in tool_name:
            server_name, actual_tool_name = tool_name.split(":", 1)

        # Dapatkan URL server dari konfigurasi
        server_config = self.mcp_servers.get(server_name, {})
        server_url = server_config.get("url", self.mcp_url)

        # Jika server tidak memiliki URL, mungkin ini adalah server command-line
        if not server_config.get("url") and server_config.get("command"):
            logger.warning(f"Server {server_name} tidak memiliki URL, hanya konfigurasi command. Tool {actual_tool_name} mungkin tidak tersedia secara langsung.")
            return None

        for attempt in range(self.max_retries):
            try:
                # Format permintaan sesuai protokol MCP
                request_data = {
                    "method": f"tools/call/{actual_tool_name}",
                    "params": parameters
                }

                # Kirim permintaan ke MCP server
                async with self.session.post(
                    f"{server_url.replace('/sse', '')}/call",
                    json=request_data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result
                    else:
                        logger.warning(f"MCP call failed with status {resp.status}")
            except Exception as e:
                logger.warning(f"MCP call attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        return None

    async def list_tools(self, server_name: str = "lms") -> Optional[list]:
        """
        Mendapatkan daftar tool yang tersedia di MCP server
        """
        if not self.is_available():
            logger.warning("MCP client not available")
            return None

        # Dapatkan URL server dari konfigurasi
        server_config = self.mcp_servers.get(server_name, {})
        server_url = server_config.get("url", self.mcp_url)

        # Jika server tidak memiliki URL, mungkin ini adalah server command-line
        if not server_config.get("url") and server_config.get("command"):
            logger.warning(f"Server {server_name} tidak memiliki URL, hanya konfigurasi command. Tidak bisa mengambil daftar tools.")
            return None

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(f"{server_url.replace('/sse', '')}/tools") as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("tools", [])
                    else:
                        logger.warning(f"Failed to list tools: {resp.status}")
            except Exception as e:
                logger.warning(f"List tools attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        return None


# Global instance
mcp_client = None


async def initialize_mcp_client():
    """
    Fungsi untuk menginisialisasi MCP client
    """
    global mcp_client
    try:
        mcp_client = MCPClient(
            max_retries=settings.mcp_max_retries if hasattr(settings, 'mcp_max_retries') else 3,
            retry_delay=settings.mcp_retry_delay if hasattr(settings, 'mcp_retry_delay') else 1.0,
        )
        connected = await mcp_client.connect()
        if not connected:
            logger.warning("MCP server connection failed, continuing without MCP tools")
    except Exception as e:
        logger.error(f"Error initializing MCP client: {e}")
        mcp_client = None


def sync_initialize_mcp_client():
    """
    Fungsi sinkron untuk menginisialisasi MCP client
    """
    global mcp_client
    try:
        import asyncio
        # Periksa apakah event loop sudah berjalan
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Tidak ada event loop yang berjalan, buat yang baru
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            mcp_client = MCPClient(
                max_retries=settings.mcp_max_retries if hasattr(settings, 'mcp_max_retries') else 3,
                retry_delay=settings.mcp_retry_delay if hasattr(settings, 'mcp_retry_delay') else 1.0,
            )
            connected = loop.run_until_complete(mcp_client.connect())
            if not connected:
                logger.warning("MCP server connection failed, continuing without MCP tools")
        else:
            # Event loop sudah berjalan, inisialisasi tanpa menjalankan loop
            # Tapi tetap coba inisialisasi client (akan menunggu beberapa saat agar server siap)
            mcp_client = MCPClient(
                max_retries=settings.mcp_max_retries if hasattr(settings, 'mcp_max_retries') else 3,
                retry_delay=settings.mcp_retry_delay if hasattr(settings, 'mcp_retry_delay') else 1.0,
            )
            # Dalam konteks event loop yang berjalan, kita harus menggunakan task untuk async connection
            import threading
            import time
            # Tunggu sebentar agar MCP server siap
            time.sleep(2)
            # Kita tidak bisa langsung await di sini, jadi hanya set instance
            logger.info("MCP client initialized in running event loop, connection will be attempted when needed")
    except Exception as e:
        logger.error(f"Error initializing MCP client: {e}")
        mcp_client = None


async def get_mcp_client() -> Optional[MCPClient]:
    """
    Fungsi untuk mendapatkan instance MCP client
    """
    global mcp_client
    if mcp_client is None:
        await initialize_mcp_client()
    elif not mcp_client.is_available():
        # Jika client sudah ada tapi tidak terhubung, coba hubungkan kembali
        await mcp_client.connect()
    return mcp_client