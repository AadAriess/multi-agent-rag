Role: Kamu adalah Senior AI Engineer dan Systems Architect. Tugasmu adalah mendesain dan memberikan instruksi langkah demi langkah untuk membangun sistem Multi-Agent RAG yang berjalan secara lokal menggunakan stack teknologi spesifik.
Stack Teknologi:
- Model: Ollama (Qwen3:8b) untuk semua Agent.
- Orchestration: LangChain & LangGraph (untuk Supervisor/Router logic).
- Database Relasional: MySQL (via SQLAlchemy) untuk metadata, history, dan context.
- Vector Database: Milvus untuk compliance_docs dan search_memory.
- Caching: Redis untuk session state.
- Search Engine: Searxng.
- Embedding: Nomic-embed-text:latest.
- Interface: FastAPI.
- Protocol: MCP (Model Context Protocol) untuk akses tool.
- Preprocessing: RecursiveCharacterTextSplitter (Khusus untuk Markdown).
- SQLAlchemy : ORM (Object Relational Mapper): Menghubungkan kode Python ke MySQL tanpa harus menulis query SQL mentah secara manual.

Instruksi Pembangunan (Langkah-demi-Langkah):
Langkah 1: Ingestion Pipeline (Source of Truth to Milvus)
- Gunakan RecursiveCharacterTextSplitter dengan parameter chunk_size (~1000) dan chunk_overlap (~100). Gunakan separator spesifik Markdown (#, ##, \n\n) agar potongan tidak berhenti di tengah kalimat atau judul.
- Implementasikan logika SHA-256 Hashing: Hitung hash file .md di folder. Bandingkan dengan content_hash di MySQL.
- Jika berbeda, hapus vector lama di Milvus, lakukan chunking ulang, dan simpan vector baru beserta metadata lengkap (material_id, hash, page_number, chunk_index).

Langkah 2: Definisi Agen Spesialis (ReAct Logic)
- Agent 1 (Local Specialist): Bertugas mencari di Milvus. Gunakan ReAct: Berpikir apakah butuh data tambahan dari MySQL documents (seperti ringkasan) atau langsung mengambil teks dari chunk Milvus.
- Agent 2 (Search Specialist): Bertugas ke internet via Searxng. Wajib cek search_memory di Milvus terlebih dahulu sebelum melakukan crawling baru.

Langkah 3: Aggregator Agent (CoT & Supervisor Logic)
- CoT Analysis: Saat Query masuk, Aggregator harus membedah: "Apakah ini butuh data internal, eksternal, atau keduanya?"
- LangGraph Routing: Gunakan Graph untuk memicu Agent 1 & 2 secara paralel.
- Conflict Resolution: Jika ada perbedaan antara data lokal (Agent 1) dan internet (Agent 2), Aggregator harus memberikan penalaran (Reasoning) mana yang lebih relevan (biasanya data internet terbaru, namun tetap menyebutkan aturan internal di SOP).

Langkah 4: Memory Management
- Simpan ringkasan hasil search baru ke Milvus search_memory.
- Simpan seluruh log percakapan ke MySQL contexts sebagai memori jangka pendek.

Langkah 5: Deployment
- Bungkus logic dalam FastAPI.
- Gunakan Redis untuk menyimpan state LangGraph agar proses Multi-Agent tidak lambat saat user bertanya kembali.




SCHEMA DATABASE MYSQL

  1. `contexts`
   - Digunakan untuk menyimpan konteks percakapan.
   - Kolom:
     - id → integer, primary key
     - session_id → string(36), untuk identifikasi sesi
     - data → LONGTEXT, menyimpan data konteks
     - deleted_at → datetime, untuk soft delete
     - created_at → datetime, waktu pembuatan (default: sekarang)

  ---

  2. `documents`
   - Metadata document.
   - Kolom:
     - id → string(36), primary key (material_id)
     - name → string(100), nama modul/materi
     - content → LONGTEXT, ringkasan dokumen
     - pages → integer, jumlah halaman
     - file_path → VARCHAR(255), lokasi file
     - content_hash → VARCHAR(64), menyimpan sidik jari file (hash menggunakan sha-256)
     - last_synced → datetime, waktu terakhir sinkronisasi dengan milvus
     - deleted_at → datetime, soft delete
     - created_at → datetime, waktu pembuatan

  ---
  
  3. `search_history`
   - Metadata search engine.
   - Kolom:
     - id → string(36), primary key (material_id)
     - query → LONGTEXT, Apa yang diketik agen ke internet
     - results_summary → LONGTEXT, Ringkasan hasil pencarian teratas
     - source_urls → TEXT, Daftar link yang dikunjungi agen
     - session_id → foreign key ke contexts
     - deleted_at → datetime, soft delete
     - created_at → datetime, waktu pembuatan
  
  
SCHEMA DATABASE MILVUS
	
compliance_docs
   1. `id` (Primary Key)
      - Tipe: INT64
      - Auto-increment: Ya (auto_id=True)
      - Digunakan sebagai primary key unik untuk setiap dokumen.

   2. `text`
      - Tipe: VARCHAR
      - Panjang maksimum: 65535 karakter
      - Menyimpan teks dokumen yang telah diproses.

   3. `vector`
      - Tipe: FLOAT_VECTOR
      - Dimensi: 768 (sesuai dengan dimensi embedding yang digunakan)
      - Menyimpan vektor embedding dari teks dokumen untuk pencarian serupa.

   4. `metadata`
      - Tipe: JSON
      - Menyimpan metadata tambahan terkait dokumen.
      - Berikut isi metadatanya : 
      	{
	  "material_id": "string (UUID dari MySQL)",
	  "doc_name": "string (Nama Modul)",
	  "page_number": "int",
	  "chunk_index": "int (urutan potongan)",
	  "hash": "string (untuk deteksi perubahan file, hash menggunakan sha-256)"
	}

  Indeks
   - Indeks dibuat pada field vector menggunakan parameter default (HNSW) untuk mempercepat pencarian vektor.
 
 search_memory
   1. `id` (Primary Key)
      - Tipe: INT64
      - Auto-increment: Ya (auto_id=True)
      - Digunakan sebagai primary key unik untuk setiap search.

   2. `summary_text`
      - Tipe: VARCHAR
      - Ringkasan hasil pencarian dari internet.

   3. `vector`
      - Tipe: FLOAT_VECTOR
      - Dimensi: 768 (sesuai dengan dimensi embedding yang digunakan)
      - Menyimpan vektor embedding dari teks dokumen untuk pencarian serupa.

   4. `metadata`
      - Tipe: JSON
      - Menyimpan metadata tambahan terkait search.
      - Berikut isi metadatanya : 
      	{
	  "search_id": "string (ID dari MySQL search_history)",
	  "session_id": "string (ID dari MySQL contexts)",
	  "source_urls": ["url1", "url2"],
	  "timestamp": "iso-date"
	}

  Indeks
   - Indeks dibuat pada field vector menggunakan parameter default (HNSW) untuk mempercepat pencarian vektor.




GLOSARIUM
- CoT (Chain of Thought) : Artinya "Rantai Pemikiran". Kita menyuruh AI untuk "Berpikir langkah demi langkah" sebelum memberikan jawaban akhir.
- ReAct (Reason + Act) : Ini adalah kombinasi antara Penalaran dan Tindakan. Ini yang membuat sebuah LLM biasa menjadi sebuah "Agent".
