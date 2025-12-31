# 📋 Langkah-Langkah Implementasi MCP di Proyek AI Service

Dokumen ini menjelaskan langkah-langkah detail untuk mengimplementasikan dan menjalankan **Model Context Protocol (MCP)** dalam proyek Anda. MCP digunakan untuk memungkinkan aplikasi berkomunikasi dengan server eksternal (tools, agen, atau model lain) melalui protokol SSE (Server-Sent Events).

---

## 🧩 Arsitektur MCP di Proyek Ini

- **MCP Client**: Diinisialisasi di `app/llms/agents/tools/mcp_tool.py`, digunakan di `main.py`.
- **MCP Server**: Dikonfigurasi di `mcp.json`, berjalan di `http://localhost:8071/sse`.
- **Tool Calling**: MCP client memanggil tool via `acall()` dan mengembalikan hasil ke LLM/agen.

---

# ✅ Langkah 1: Siapkan File Konfigurasi `mcp.json`

File ini sudah ada di root project Anda:
```json
{
  "mcpServers": {
    "lms": {
      "url": "http://localhost:8071/sse"
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sequential-thinking", "-y"]
    }
  }
}
```

### ⚙️ Jika Ingin Menambahkan Server MCP Baru:
Tambahkan entri baru di `mcpServers`:
```json
"my-new-server": {
  "url": "http://localhost:8080/sse"
}
```
Atau jika ingin jalankan via command:
```json
"my-tool-server": {
  "command": "python",
  "args": ["tools_server.py"]
}
```

---

# ✅ Langkah 2: Jalankan Server MCP

Anda perlu menjalankan server MCP sebelum menjalankan aplikasi Anda.

## 📌 Untuk Server `lms` (localhost:8071)
Jika server ini belum ada, Anda harus membuatnya.

### Contoh Sederhana Server MCP (Python + FastAPI):
Buat file `mcp_server.py`:
```python
from fastapi import FastAPI
from fastmcp import Server, Tool
import asyncio

app = FastAPI()

# Definisikan tool MCP
class MyTool(Tool):
    name = "get_weather"
    description = "Get weather for a city"

    async def call(self, city: str) -> dict:
        return {"city": city, "weather": "sunny"}

# Buat server MCP
server = Server()
server.add_tool(MyTool())

@app.get("/sse")
async def sse():
    return await server.sse()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8071)
```

Jalankan server:
```bash
pip install fastapi uvicorn fastmcp
python mcp_server.py
```
→ Sekarang server MCP berjalan di `http://localhost:8071/sse`.

## 📌 Untuk Server `sequential-thinking`
Ini sudah siap pakai via npm/npx:
```bash
npx @modelcontextprotocol/server-sequential-thinking -y
```

---

# ✅ Langkah 3: Integrasi MCP Client di Aplikasi

Anda sudah memiliki integrasi ini di `app/main.py` dan `app/llms/agents/tools/mcp_tool.py`.

### ✅ Pastikan MCP Client Diinisialisasi:
Di `app/llms/agents/tools/mcp_tool.py`:
```python
from app.llms.core.mcp.mcp_client import MCPClient
from app.core.config import settings

try:
    mcp_client = MCPClient(
        max_retries=settings.mcp_max_retries,
        retry_delay=settings.mcp_retry_delay,
    )
except Exception as e:
    mcp_client = None
```
→ Ini sudah benar.

### ✅ Hubungkan MCP Client Saat Startup:
Di `app/main.py`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MCP server
    if mcp_client:
        connected = await mcp_client.connect()
        if not connected:
            log.warning("MCP server connection failed, continuing without MCP tools")
    else:
        log.warning("MCP client not available, continuing without MCP tools")
    yield
```
→ Ini juga sudah benar.

---

# ✅ Langkah 4: Gunakan MCP Tools di Dalam Aplikasi

Anda bisa menggunakan MCP tools di dalam agen atau router.

### Contoh: Panggil Tool MCP di `chat.py`
Di `app/api/v1/routers/chat.py`, tambahkan:
```python
from app.llms.agents.tools.mcp_tool import mcp_client

async def chat_with_mcp(user_input: str):
    if mcp_client and mcp_client.is_available():
        result = await mcp_client.acall("get_weather", {"city": "Jakarta"})
        return result.content
    else:
        return "MCP tools not available"
```

---

# ✅ Langkah 5: Tambahkan Tool MCP Baru

Jika Anda ingin menambahkan tool MCP baru:

### 1. Buat Tool di Server MCP
Contoh di `mcp_server.py`:
```python
class GetTimeTool(Tool):
    name = "get_time"
    description = "Get current time"

    async def call(self) -> dict:
        from datetime import datetime
        return {"time": datetime.now().isoformat()}
```
Tambahkan ke server:
```python
server.add_tool(GetTimeTool())
```

### 2. Gunakan Tool di Client
Di aplikasi Anda:
```python
result = await mcp_client.acall("get_time", {})
```

---

# ✅ Langkah 6: Debug & Monitoring

### 📊 Log Koneksi MCP
Di `main.py`, Anda sudah punya log:
```python
log.info("Connecting to MCP server...")
log.info("✅ MCP server connected successfully")
log.warning("MCP server connection failed...")
```

### 🛠️ Cek Status MCP Client
Gunakan fungsi:
```python
if mcp_client.is_available():
    print("MCP client is connected")
else:
    print("MCP client is not connected")
```

---

# ✅ Langkah 7: Deploy MCP Server (Opsional)

Jika Anda ingin menjalankan MCP server di production:

### 🐳 Dockerize MCP Server
Buat `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py .

EXPOSE 8071

CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8071"]
```

Buat `requirements.txt`:
```
fastapi
uvicorn
fastmcp
```

Build dan jalankan:
```bash
docker build -t mcp-server .
docker run -p 8071:8071 mcp-server
```

---

## 💡 Tips Tambahan:

- Jika server MCP tidak berjalan, aplikasi akan tetap berjalan — tapi tanpa fitur MCP.
- Gunakan `max_retries` dan `retry_delay` di `config.py` untuk menyesuaikan toleransi koneksi.
- Jika ingin MCP server berjalan otomatis saat aplikasi start, Anda bisa tambahkan script di `run.py` atau `main.py`.

---

> 📝 **Catatan**: Dokumen ini dibuat berdasarkan kode proyek Anda. Jika Anda ingin menambahkan fitur baru atau mengubah arsitektur, silakan sesuaikan langkah-langkah di atas.
