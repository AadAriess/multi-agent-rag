Validasi Langkah
Berikut adalah alur detail dari Query ke Output khusus untuk sistem Multi-Agent:
1. Tahap Penerimaan (Aggregator Agent) : Semua dimulai dari Aggregator Agent. Sebelum Aggregator membagi tugas (Delegasi), dia melakukan CoT (Chain of Thought) untuk merumuskan rencana.
	- Query Analysis: Ia membedah pertanyaan kamu. Misal: "Bandingkan aturan cuti di SOP kita dengan regulasi pemerintah terbaru."
	- Task Decomposition: Ia sadar ini adalah tugas dua arah (Internal vs Eksternal). Ia tidak mengerjakan sendiri, tapi membagi tugas tersebut.

2. Tahap Delegasi (Paralel) : Aggregator mengirimkan instruksi ke dua agen spesialis secara bersamaan (Paralel):
	- Ke Agent 1 (Local Data Specialist): "Cari di Milvus compliance_docs tentang aturan cuti, ambil teks aslinya dari folder Markdown."
	- Ke Agent 2 (Search Specialist): "Cari di internet tentang regulasi pemerintah terbaru tahun 2024/2025 mengenai hak cuti karyawan."

3. Tahap Kerja Spesialis (Agentic Loop) : Masing-masing agen ini memiliki siklus ReAct (Berpikir -> Bertindak -> Amati / Reason + Act) sendiri:
	- Agent 1 mungkin menemukan bahwa dokumen di Milvus versinya sudah lama (berdasarkan metadata hash). Ia bisa melapor ke Aggregator: "Data internal ada, tapi versinya lama."
	- Agent 2 melakukan browsing. Ia melihat hasil di search_memory (Milvus) dulu. Kalau tidak ada, ia memanggil Search Engine Server.

4. Tahap Sintesis & Kritik (The Planning Layer) : Setelah Agent 1 dan Agent 2 kembali membawa data, mereka tidak langsung memberikannya ke kamu. Data tersebut masuk kembali ke Aggregator Agent.
	- Reasoning: Aggregator membandingkan kedua data tersebut.
	- Conflict Resolution: Contoh : Jika Agent 1 bilang "Cuti 12 hari" dan Agent 2 (Internet) bilang "Aturan baru 14 hari", Aggregator akan menyusun jawaban yang menjelaskan perbedaan tersebut, bukan malah 	bingung.

5. Tahap Finalisasi & Memory Update : Aggregator menyusun jawaban akhir yang komprehensif.
	- Long-term Memory Update: Hasil pencarian internet yang baru disimpan ke Milvus search_memory agar besok-besok Agent 2 tidak perlu browsing lagi untuk hal yang sama.
	- Short-term Memory Update: Percakapan ini disimpan ke MySQL contexts agar konteks "perbandingan cuti" ini diingat untuk pertanyaan kamu selanjutnya.

6. Output : Hasil yang kamu terima bukan sekadar potongan teks, melainkan analisis lengkap yang bersumber dari berbagai tempat (Local & Search Engine) yang sudah diverifikasi kebenarannya oleh si Aggregator.




DAFTAR TOOLS
- MySQL : Structured Storage: Menyimpan katalog dokumen (documents), log pencarian (search_history), dan riwayat chat (contexts).
- SQLAlchemy : ORM (Object Relational Mapper): Menghubungkan kode Python ke MySQL tanpa harus menulis query SQL mentah secara manual.
- Milvus : Vector Storage: Menyimpan embedding dokumen (compliance_docs) dan memori pencarian (search_memory) untuk pencarian semantik.
- Redis Cache : Speed Layer: Menyimpan session state yang sedang aktif atau hasil query yang sering dipakai agar tidak membebani MySQL/Milvus.
- MCP (Model Context Protocol) : Standardized Interface: Menjadi jembatan standar agar Agent bisa mengakses file lokal, database, atau tools pihak ketiga dengan format yang sama.
- LangChain : Orchestrator: Untuk mengatur alur "siapa panggil siapa", mengelola prompt template, dan menangani memory buffer antar Agen.
- Ollama (Qwen3:8b) : Local Inference: Mesin kecerdasan yang menjalankan proses CoT, ReAct, dan sintesis akhir secara lokal.
- Nomic-Embed-Text : Encoder: Mengubah teks manusia menjadi angka (vektor) agar bisa diproses oleh Milvus.
- Searxng : Privacy Search Engine: Agregator pencarian internet yang menjaga privasi dan memberikan data bersih ke Agent 2.
- FastAPI : Untuk membuat User Interface (UI) dan Backend API.
- Text Splitter / Chunking Library : RecursiveCharacterTextSplitter alat untuk memotong file Markdown menjadi bagian-bagian kecil secara cerdas (tidak memotong kalimat di tengah jalan).
- Supervisor / Router Logic : LangGraph untuk mengatur lalu lintas komunikasi
