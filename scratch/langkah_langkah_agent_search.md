Alur Kerja Agent 2 (Step-by-Step)
1. Menerima Perintah dari Aggregator
Agent 2 menerima query pencarian dari Aggregator.
Input: query (misal: "Aturan Administrasi Kemenhan 2025") dan session_id.

2. Fase Pencarian Memori (Pre-Search)
Sebelum ke internet, Agent 2 melakukan pengecekan ke Milvus koleksi search_memory.
Aksi: Melakukan pencarian vektor (similarity search) menggunakan embedding dari query.
Hasil:
    - Jika Tidak Ada: Lanjut ke Langkah 3 (Browsing).
    - Jika Ada (Hit): Ambil metadata (JSON). Baca timestamp dan search_id.
        - Validasi ke MySQL: Gunakan search_id untuk query ke tabel search_history di MySQL. Cek apakah data tersebut masih dianggap "fresh" (misal < 7 hari).
        - Kondisi Segar: Ambil results_summary dari MySQL, lalu kembalikan ke Aggregator. (Selesai).
        - Kondisi Basi: Lanjut ke Langkah 3 (Browsing) untuk update data.

3. Fase Eksekusi Tool (Browsing)
Jika data tidak ditemukan atau sudah usang:
- Aksi: Agent 2 memanggil tool Searxng.
- Proses: Mengumpulkan hasil pencarian mentah, mengunjungi URL yang paling relevan, dan menyusun "Kandidat Jawaban".
- Output ke Aggregator: Memberikan ringkasan temuan dan daftar URL sumber.

4. Fase Verifikasi Aggregator (Sintesis)
- Aggregator menerima temuan Agent 2.
- Aggregator menyaring fakta yang benar dan menyusun Jawaban Final.
- Aggregator memberikan instruksi: "Simpan ini ke memori."

5. Fase Sinkronisasi Data
Setelah jawaban final siap, Agent 2 melakukan penyimpanan paralel:
A. Simpan ke MySQL (search_history):
Sistem men-generate UUID baru sebagai id (material_id).
Melakukan INSERT ke tabel search_history:
query: Teks pencarian.
results_summary: Ringkasan bersih yang sudah divalidasi Aggregator.
source_urls: Daftar link yang valid.
session_id: ID sesi aktif.

B. Simpan ke Milvus (search_memory):
Sistem mengubah results_summary menjadi vektor.
Melakukan INSERT ke Milvus:
summary_text: Ringkasan yang sama.
vector: Hasil embedding.
metadata: Masukkan JSON yang berisi search_id (ID yang baru saja dibuat di MySQL), session_id, source_urls, dan timestamp (ISO-date sekarang).