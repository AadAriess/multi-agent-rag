# OriensSpace AI

Proyek ini adalah platform AI untuk berbagai kebutuhan, dengan fokus pada modularitas dan skalabilitas.

## Struktur Proyek

```
oriensspace-ai/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── routers/
│   │           ├── index.py
│   │           └── chatbot.py
│   ├── core/
│   ├── database/
│   ├── llms/
│   │   └── agents/
│   │       └── chatbot/
│   │           ├── __init__.py
│   │           └── rag_agent.py
│   ├── main.py
│   ├── models/
│   ├── services/
│   └── utils/
├── migrations/
├── static/
├── templates/
├── tests/
├── .env
├── docker-compose.yml
├── pyproject.toml
├── run.py
└── README.md
```

### Penjelasan Struktur

- `app/` - Berisi kode aplikasi utama
  - `api/` - Endpoint API
    - `v1/routers/` - Router untuk API v1
      - `index.py` - Router utama
      - `chatbot.py` - Router untuk endpoint chatbot
  - `core/` - Fungsi-fungsi inti aplikasi
  - `database/` - Konfigurasi dan model database
  - `llms/` - Konfigurasi dan manajemen LLM
    - `agents/chatbot/` - Logika agen chatbot
      - `rag_agent.py` - Implementasi RAG untuk chatbot
  - `models/` - Model data
  - `services/` - Business logic
  - `utils/` - Fungsi-fungsi utilitas
- `migrations/` - Migrasi database
- `static/` - File statis (CSS, JS, gambar)
- `templates/` - Template HTML
- `tests/` - Uji coba aplikasi

## Instalasi

1. Instal uv (jika belum terinstal):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Buat virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. Instal dependensi:
   ```bash
   uv pip install -e .
   ```

4. Atur variabel lingkungan:
   ```bash
   cp .env.example .env
   # Edit .env sesuai kebutuhan
   ```

5. Jalankan aplikasi:
   ```bash
   uv run python run.py
   # atau
   python -m run
   ```

## Pengembangan

Untuk pengembangan, Anda dapat menginstal dependensi pengembangan:
```bash
uv pip install -e ".[dev]"
```

## Kontribusi

Silakan buat pull request untuk kontribusi. Pastikan untuk menulis uji coba yang relevan.