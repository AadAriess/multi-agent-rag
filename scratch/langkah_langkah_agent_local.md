Alur Kerja Agent 1 (Local Specialist)
1. Menerima Tugas dari Aggregator
Agent 1 menerima query dan instruksi untuk mencari informasi di dokumen internal.
Input: query (misal: "Prosedur pengadaan alat pertahanan") dan session_id.

2. Pencarian Semantik di Milvus (compliance_docs)
Agent 1 melakukan pencarian vektor pada koleksi compliance_docs.
- Aksi: Melakukan similarity search menggunakan embedding dari query.
- Filter Metadata: Agent 1 hanya mengambil chunk teks yang memiliki skor kemiripan tinggi.
- Output Awal: Mendapatkan teks (text) dan metadata (material_id, page_number, hash).

3. Verifikasi Integritas ke MySQL (documents)
Ini adalah langkah krusial untuk memastikan dokumen yang ditemukan di Milvus masih valid dan tidak sedang berubah/dihapus.
- Aksi: Menggunakan material_id dari metadata Milvus, Agent 1 melakukan query ke MySQL tabel documents via SQLAlchemy.
- Pengecekan Hash: * Agent 1 membandingkan hash yang ada di Milvus dengan content_hash yang ada di MySQL.
- Kondisi Cocok: Dokumen valid, lanjutkan proses.
- Kondisi Tidak Cocok: Berikan peringatan ke Aggregator bahwa "Dokumen sedang diperbarui, hasil mungkin tidak akurat" atau picu fungsi sinkronisasi ulang (Ingestion).

4. Pengambilan Konteks Tambahan (Context Enrichment)
Kadang potongan teks (chunk) di Milvus terlalu pendek.
- Aksi: Jika Aggregator butuh gambaran besar, Agent 1 mengambil kolom content (ringkasan dokumen) dari MySQL tabel documents berdasarkan material_id.
- Manfaat: Agent 1 bisa memberikan jawaban: "Berdasarkan potongan teks di halaman 5 (Milvus) dan ringkasan modul X (MySQL), prosedurnya adalah..."

5. Pelaporan ke Aggregator
Agent 1 menyusun laporan terstruktur yang berisi:
- Potongan teks asli dari Milvus.
- Metadata dokumen (Nama modul, halaman).
- Status validasi (Apakah hash cocok/dokumen terverifikasi).