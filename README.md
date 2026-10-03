# Parallel Log File Analyzer — Farizal Muztahidin (247006111044)

## 1. Skenario Eksperimen

**Judul:** *Parallel Log File Analyzer dengan Hybrid Multithreading–Multiprocessing* —
mengukur dan membandingkan waktu, throughput, speedup, dan efisiensi 4 pendekatan
(Sequential, Multithread, Multiprocessing, Hybrid) dalam menganalisis 32 file log
web server (±320 MB, 1.036.475 baris), dengan variasi jumlah thread (1/2/4/8),
jumlah process (1/2/4/8), konfigurasi hybrid (2p×2t, 4p×2t, 4p×4t, 8p×2t),
dan jumlah file (4/8/16/32).

**Permasalahan:** file log server nyata berukuran besar (di sini `access.log`
±3,50 GB) sehingga analisis sequential baris-per-baris menjadi lambat dan tidak
memanfaatkan CPU multi-core (10 core fisik / 16 thread).

**Solusi — Desain Solusi (bandingkan 4 pendekatan: Sequential, Multithread,
Multiprocessing, Hybrid).**

*Parallel Log File Analyzer* — menganalisis 32 file log web server (±320 MB,
1.036.475 baris) dan menghitung metrik agregat (total baris, distribusi HTTP
status code, top 10 IP, kemunculan keyword `timeout`) secara paralel.

Masalah ini diselesaikan dengan membagi 32 file menjadi beberapa kelompok
(task) yang diproses secara bersamaan menggunakan multithreading atau
multiprocessing. Setiap file diparsing baris-per-baris (regex: IP, status code,
keyword), kemudian sistem mencatat waktu mulai, waktu selesai, dan durasi tiap
run, lalu menghitung throughput (baris/detik), speedup (vs Sequential), dan
efisiensi (speedup ÷ jumlah worker). Setiap task memakai counter lokal yang
digabung di akhir (merge), sehingga tidak butuh lock namun hasilnya tetap
benar. Varian bug (counter global tanpa lock) sengaja disertakan untuk
menunjukkan race condition: hasilnya salah dan berbeda setiap run. Varian
hybrid menggabungkan keduanya — process di level atas, thread di dalam tiap
process — agar komputasi berat paralel di core berbeda sekaligus menutupi
waktu tunggu I/O. Perbandingan keempatnya:

| Pendekatan      | Pembagian kerja                           | Kelebihan                               | Keterbatasan                      |
|-----------------|-------------------------------------------|-----------------------------------------|-----------------------------------|
| Sequential      | 1 penerima, file satu per satu            | Sederhana, hasil pasti benar (baseline) | Lambat, 1 core saja               |
| Multithread     | 1 file per thread                         | Ringan, bagus saat menunggu I/O         | GIL: stagnan untuk regex (CPU)    |
| Multiprocessing | 1 file per process                        | Paralel sejati per core, tercepat       | Overhead lahirkan proses + pickle |
| Hybrid          | Round-robin ke proses, thread di dalamnya | Kedua keunggulan sekaligus              | Kompleksitas + overhead ganda     |

## 2. Arsitektur Sistem

**Tahap 1 — Input.** Satu file `dataset/raw/access.log` (±3,50 GB, format
Combined Log: IP, tanggal, request, status code, bytes). Disiapkan manual oleh
user dan hanya dibaca (read-only).

**Tahap 2 — Split & Dispatch.** `prepare_dataset.py` memotong 320 MB cuplikan
menjadi 32 file @ ±10 MB (`part_001`…`part_032`) per baris utuh, plus
`manifest.json` (nama file, jumlah baris). Dispatcher (`run_all_experiments.py`
atau main tiap mode) membaca manifest dan membagi daftar file ke unit kerja:
sequential = 1 penerima; multithread = N thread (1 file per thread);
multiprocessing = N proses (1 file per proses); hybrid = file dibagi round-robin
ke proses, lalu tiap proses membagi bagiannya ke thread internal.

**Tahap 3 — Parallel Processing Framework.** Setiap worker menjalankan alur
identik: terima file → `parse_chunk` (regex: IP = token pertama, status = 3 digit
setelah request, keyword `timeout` case-insensitive, level log = 0) → hasilkan
counter lokal. Varian bug menulis ke satu counter global tanpa lock (race
condition); varian final memakai counter lokal. Waktu tiap run dicatat dengan
`perf_counter` ke `results/logs/`.

**Tahap 4 — Collect & Aggregate.** `merge_results` menjumlahkan counter lokal:
hybrid dua tingkat (thread → proses → utama), mode lain satu tingkat → agregat
global (total baris, distribusi status, top 10 IP, keyword).

**Tahap 5 — Results & Metrics.** Setiap run menghasilkan waktu total, throughput
(baris/detik), speedup (vs sequential pada jumlah file yang sama), dan efisiensi
(speedup ÷ jumlah worker). Tersimpan di `hasil_eksperimen.csv` (52 baris) →
`plot_results.py` → 5 grafik + Markdown (tabel gabungan, Tabel A-thread,
B-process, C-file).

## 3. Skenario Eksperimen 

**3.1 Bagaimana program menjalankan eksperimen (`src/run_all_experiments.py`).**
Loop terluar adalah jumlah file (4 → 8 → 16 → 32): tiap volume mengulang seluruh
13 konfigurasi agar perbandingan adil pada data yang sama. Tiap blok volume
diawali Sequential sebagai baseline blok itu (speedup konfigurasi lain dihitung
terhadapnya, bukan terhadap volume lain). Tiap kombinasi diulang 3× dan diambil
median agar tahan terhadap satu run yang kena gangguan sesaat. Total
4 × 13 × 3 = 156 run; tiap run mencatat waktu, throughput, speedup, efisiensi
ke `hasil_eksperimen.csv` beserta log.

**3.2 Implementasi code dan paralelisme.**
Parsing (`log_parser.py`): regex per baris → counter lokal per unit kerja →
`merge_results` (penjumlahan murni, tanpa lock). Sequential: loop file satu per
satu (1 proses 1 thread). Multithread-final: `ThreadPoolExecutor`, 1 file per
thread, counter lokal + merge; berbagi 1 GIL sehingga hanya menutupi waktu I/O
dan stagnan untuk regex (CPU-bound). Multithread-bug: semua thread menulis satu
counter global via read → modify → write terpisah plus `sleep(0)` pelepas GIL
sehingga update hilang dan hasil berbeda tiap run. Multiprocessing:
`ProcessPoolExecutor`, 1 file per proses; tiap proses punya GIL dan memori
sendiri (spawn Windows, worker di level modul agar bisa di-pickle) sehingga
paralel sejati di core berbeda, dikurangi overhead melahirkan proses. Hybrid:
proses di atas, thread di dalamnya; merge dua tingkat. Visualisasi
(`plot_results.py`): membaca CSV apa adanya tanpa data dummy → 3 grafik wajib
+ 2 bonus + Markdown (gabungan, Tabel A/B/C).

**3.3 Hasil yang diharapkan.**
Waktu sequential naik proporsional jumlah file (8 file ≈ 2× waktu 4 file, dst).
Multithread th=1 ≈ sequential; th=2/4/8 stagnan atau sedikit lebih baik (ciri
GIL, bukan kegagalan). Multiprocessing/hybrid naik hingga ~4–8× lalu melandai;
efisiensi turun seiring worker bertambah. `multithread_final` identik sequential;
`multithread_bug` berbeda dan tidak stabil antar-run. Batas validitas: speedup
tidak dapat melebihi jumlah core fisik (10); selebihnya adalah anomali
pengukuran yang wajib diinvestigasi (re-run saat PC idle), bukan prestasi.
Artefak akhir: CSV 52 baris, 5 PNG, 1 Markdown — angka inilah yang masuk
laporan Bagian C.

## 4. Dataset (disiapkan manual oleh user — PRD Bagian 0.4)

1. Buka `https://www.kaggle.com/datasets/eliasdabbas/web-server-access-logs`,
   klik **Download** (perlu login Kaggle). Total unduhan menurut deskripsi
   Kaggle: ±3,3 GB.
2. Ekstrak file `.zip` (Windows: klik kanan → *Extract All*).
3. Pindahkan **file log hasil ekstrak** (bukan file zip) ke `dataset/raw/`.
   File yang dipakai di sini: `access.log` = 3.502.440.823 byte (±3,50 GB).
4. Jangan mengubah isi file log.
5. Validasi dataset:
   ```powershell
   python -m src.check_dataset
   ```

## 5. Data siap olah (prepared)

File 3,50 GB terlalu besar untuk diuji langsung, jadi diambil cuplikan
320 MB lalu dipotong menjadi 32 file @ ±10 MB:

| Item            | Nilai                                |
|-----------------|--------------------------------------|
| File sumber     | `dataset/raw/access.log` (±3,50 GB)  |
| Total cuplikan  | 320 MB                               |
| Ukuran per file | ±10 MB                               |
| Jumlah file     | 32 (`part_001.log` … `part_032.log`) |
| Total baris     | 1.036.475                            |
| Daftar file     | `dataset/prepared/manifest.json`     |

Perintah pembuatnya (cukup dijalankan sekali):

```powershell
python -m src.prepare_dataset --source access.log --sample-mb 320 --target-mb 10
```

Kenapa 32 file? Agar pada konfigurasi terbesar (8 process × 2 thread =
16 pekerja) setiap pekerja kebagian tepat 2 file — tidak ada yang menganggur:

| Konfigurasi     | Pekerja | File per pekerja |
|-----------------|---------|------------------|
| Sequential      | 1       | 32               |
| Multithread 8   | 8       | 4                |
| Multiprocessing | 8       | 4                |
| Hybrid 8p × 2t  | 16      | 2                |

## 6. Instalasi

```powershell
pip install -r requirements.txt
```

Butuh Python 3.10+ (teruji di Windows, 10 core / 16 thread).

## 7. Cara menjalankan eksperimen

```powershell
python -m src.check_dataset        # 1. validasi dataset/raw (read-only)
python -m src.prepare_dataset      # 2. potong data ke dataset/prepared + manifest.json
python -m src.sequential           # 3. baseline pembanding
python -m src.run_all_experiments  # 4. benchmark lengkap (tutup aplikasi berat dulu!)
python -m src.plot_results         # 5. grafik + tabel hasil
```

Hasil tersimpan di `results/tables/hasil_eksperimen.csv` dan
grafik di `results/figures/`.

## 8. Mengubah parameter eksperimen (untuk dosen/user)

Semua angka percobaan berasal dari `config.yaml` bagian `experiment`
dan bisa ditimpa lewat argumen baris perintah (CLI) tanpa mengedit file:

| Yang diubah      | Lokasi / CLI                                               | Contoh                                                        |
|------------------|------------------------------------------------------------|---------------------------------------------------------------|
| Jumlah thread    | `config.yaml` → `experiment.threads` / `--threads`         | `python -m src.run_all_experiments --threads 2,4`             |
| Jumlah process   | `config.yaml` → `experiment.processes` / `--processes`     | `python -m src.run_all_experiments --processes 2,4`           |
| Kombinasi hybrid | `config.yaml` → `experiment.hybrid_configs` / `--hybrid`   | `python -m src.run_all_experiments --hybrid "2x2;4x2"`        |
| Jumlah file      | `config.yaml` → `experiment.file_counts` / `--file-counts` | `python -m src.run_all_experiments --file-counts 4,8,16`      |
| Pengulangan      | `config.yaml` → `experiment.repetitions` / `--repetitions` | `python -m src.run_all_experiments --repetitions 5`           |
| Ukuran cuplikan  | `prepare_dataset` → `--sample-mb`, `--target-mb`           | `python -m src.prepare_dataset --sample-mb 160 --target-mb 5` |
| Coba 1 mode saja | tiap mode → `--max-files`, `--threads`/`--processes`       | `python -m src.multithread_final --max-files 2 --threads 4`   |

Dua aturan yang perlu diingat:

1. **Jumlah file tidak boleh melebihi isi manifest.** Jika `--file-counts`
   lebih besar dari file yang tersedia (sekarang 32), program otomatis
   memakai yang tersedia dan menampilkan peringatan.
2. **Setiap ganti dataset/parameter → ulangi benchmark + plot.**
   File CSV lama otomatis kedaluwarsa karena datanya sudah berbeda.

## 9. Catatan teknis

- Benchmark memakai `time.perf_counter()` dan tiap kombinasi diulang
  3× lalu diambil nilai tengah (median) agar tahan terhadap gangguan sesaat.
- Multiprocessing di Windows memakai `spawn`: fungsi pekerja didefinisikan
  di level modul dan pool hanya dijalankan di bawah `if __name__ == "__main__":`.
- Thread Python berbagi GIL sehingga tidak mempercepat kerja CPU (regex);
  proses terpisah masing-masing punya GIL sendiri sehingga benar-benar
  paralel di core yang berbeda.
- Batas wajar: speedup tidak dapat melebihi jumlah core fisik (10).
  Jika terukur lebih, tandai sebagai anomali pengukuran, bukan prestasi.
