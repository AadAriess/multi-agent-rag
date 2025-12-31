# Panduan Penggunaan UV untuk Proyek OriensSpace AI

UV adalah package manager Python yang cepat yang digunakan dalam proyek ini untuk mengelola dependensi dan virtual environment.

## Instalasi UV

Jika Anda belum menginstal UV, Anda dapat melakukannya dengan perintah berikut:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Penggunaan Dasar

### Membuat Virtual Environment
```bash
uv venv
source .venv/bin/activate
```

Secara default, perintah di atas akan membuat virtual environment di direktori `.venv`.

### Menginstal Dependensi
```bash
# Instal semua dependensi dari pyproject.toml
uv pip install -e .

# Instal dependensi pengembangan
uv pip install -e ".[dev]"
```

### Menjalankan Aplikasi
```bash
uv run python run.py
```

### Menginstal Package Baru
```bash
uv pip install nama_package
```

Package yang diinstal akan ditambahkan ke `pyproject.toml` secara otomatis jika Anda menggunakan perintah `uv add` (jika fitur ini tersedia).

## Perintah Umum

- `uv venv` - Membuat virtual environment
- `uv pip install` - Menginstal package
- `uv run` - Menjalankan perintah dalam environment
- `uv sync` - Menginstal semua dependensi dari pyproject.toml
- `uv lock` - Menghasilkan uv.lock dari pyproject.toml

## Keunggulan UV

- **Kecepatan**: UV jauh lebih cepat daripada pip dalam menginstal package
- **Konsistensi**: Menghasilkan environment yang konsisten
- **Manajemen dependensi**: Lebih baik dalam menangani dependensi yang kompleks
- **Kemudahan penggunaan**: Perintah yang intuitif dan mudah diingat

## Integrasi dengan Proyek Ini

Proyek OriensSpace AI menggunakan UV untuk:
- Mengelola dependensi Python
- Membuat dan mengelola virtual environment
- Menjalankan aplikasi dan skrip
- Mengelola dependensi pengembangan