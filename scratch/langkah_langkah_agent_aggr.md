Alur Kerja Agent Aggregator (The Mastermind)
1. Fase Inisialisasi & Konteks (MySQL contexts)
Saat user mengirimkan input, Aggregator pertama kali berinteraksi dengan tabel contexts.
- Aksi: Mengambil kolom data berdasarkan session_id.
- Tujuan: Memahami apakah pertanyaan sekarang berhubungan dengan pertanyaan sebelumnya (misal: pertanyaan "Kenapa begitu?" setelah bertanya soal aturan).
- Logika Context Windowing: * Jika data ditemukan, Aggregator membedah JSON tersebut: Context = summary + history.
    - Aggregator menghitung jumlah objek di dalam array history.
    - Penting: Jika history kosong tapi summary ada, Aggregator tetap memberikan summary ke Agent 1 & 2 sebagai "Latar Belakang Dasar".

2. Fase Perencanaan (Sequential Thinking)
Aggregator menggunakan tool sequential_thinking untuk menganalisis query:
- Analisis: 
    - "Apakah user tanya soal aturan internal (Agent 1), berita luar (Agent 2), atau perbandingan keduanya?"
    - "Apakah pertanyaan ini merujuk ke kata ganti (misal: 'itu', 'tersebut') yang ada di summary atau history?"
- Keputusan: Membuat rencana eksekusi (paralel atau sekuensial).

3. Fase Delegasi & Orchestration (LangGraph)
Aggregator memicu Agent 1 dan Agent 2.
- Agent 1: Mencari di compliance_docs & tabel documents.
- Agent 2: Mencari di search_memory & tabel search_history (dan internet jika perlu).
- State Management: Selama menunggu, Aggregator menyimpan status kerja ke Redis agar sesi tidak hilang.

4. Fase Sintesis & Conflict Resolution
Setelah Agent 1 dan 2 melapor, Aggregator menerima data yang kaya akan metadata.
- Aksi: Membandingkan temuan.
- Jika Agent 1 menemukan aturan di documents.name "SOP 2022" dan Agent 2 menemukan berita terbaru 2025.
- Aggregator menyusun narasi: "Berdasarkan SOP internal (modul: {doc_name}), aturannya adalah A, namun regulasi terbaru yang ditemukan di internet menunjukkan perubahan menjadi B."

5. Fase Finalisasi & Update Database (Post-Process)
Sebelum menyimpan, Aggregator melakukan Maintenance Memori:
- Threshold Check: Jika jumlah pesan di history > 10 (angka batas opsional):
    - Summarize: Aggregator memicu LLM untuk meringkas 10 pesan tersebut menjadi 1-2 paragraf padat.
    - Update Summary: Hasil ringkasan baru digabungkan dengan summary lama.
    - Purge History: Array history dikosongkan (di-reset).
- Append: Masukkan query dan response terbaru ke dalam array history yang baru/kosong tadi.
- Write to MySQL: Simpan objek JSON lengkap (summary + history terbaru) ke kolom data.




DATA DI TABEL CONTEXTS MYSQL
KETIKA MASIH 10 ATAU KURANG : 
[
  {
    "query": "Apa itu PERMENHAN No. 30 Tahun 2019?",
    "response": "...", 
    "timestamp": "2025-12-30T13:43:38"
  },
  {
    "query": "Apa saja jenis surat resmi yang diatur?",
    "response": "...", 
    "timestamp": "2025-12-30T13:45:38"
  }
]

KETIKA SUDAH DIATAS 10 (SUMMARY PESAN BAGIAN RESPONSE NYA DARI PESAN 1-10, YANG KE 11 NANTI MASUK JADI HISTORY): 
{
  "summary": "User menanyakan dasar hukum PERMENHAN 30/2019. Diskusi mencakup definisi administrasi umum, struktur surat perintah yang harus ditandatangani pejabat berwenang, dan mekanisme paraf surat sebelum diajukan ke Sekjen.",
  "history": [
    {
      "query": "Lalu bagaimana jika pejabat tersebut berhalangan hadir?",
      "response": "Berdasarkan regulasi, surat dapat diserahkan ke pejabat lain/tata usaha dengan persetujuan 'atas nama'...",
      "timestamp": "2025-12-30T14:45:00"
    }
  ]
}