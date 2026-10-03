"""Visualisasi hasil: 3 grafik wajib + tabel Markdown (+2 opsional).

- Baca results/tables/hasil_eksperimen.csv. Jika tidak ada -> berhenti
  dengan pesan jelas. JANGAN membuat data dummy (PRD 6.8).
- Wajib: waktu_vs_thread.png, waktu_vs_process.png, speedup_vs_konfigurasi.png.
- Opsional nilai tambah: throughput_vs_konfigurasi.png, efisiensi_vs_konfigurasi.png.
- Tabel: results/tables/hasil_eksperimen.md (gabungan + Tabel A/B/C per 10.2.1).
"""
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

CSV_COLS = ["No", "Mode", "Thread", "Process", "File", "Total Baris",
            "Waktu (s)", "Throughput", "Speedup", "Efisiensi"]


def _label(row) -> str:
    if row["Mode"] == "Sequential":
        return "seq"
    if row["Mode"] == "Multithread":
        return f"mt-{int(row['Thread'])}t"
    if row["Mode"] == "Multiprocessing":
        return f"mp-{int(row['Process'])}p"
    return f"hy-{int(row['Process'])}pX{int(row['Thread'])}t"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/tables/hasil_eksperimen.csv")
    ap.add_argument("--figdir", default="results/figures")
    ap.add_argument("--md", default="results/tables/hasil_eksperimen.md")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: {csv_path} tidak ditemukan. Jalankan dulu: python -m src.run_all_experiments")
        sys.exit(1)
    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"ERROR: {csv_path} kosong.")
        sys.exit(1)

    figdir = Path(args.figdir)
    figdir.mkdir(parents=True, exist_ok=True)
    df["Konfigurasi"] = df.apply(_label, axis=1)

    # 1. Waktu vs Jumlah Thread (mode Multithread, satu garis per File).
    mt = df[df["Mode"] == "Multithread"].sort_values(["File", "Thread"])
    plt.figure()
    for nf, g in mt.groupby("File"):
        plt.plot(g["Thread"], g["Waktu (s)"], marker="o", label=f"{nf} file")
    plt.xlabel("Jumlah Thread")
    plt.ylabel("Waktu (s)")
    plt.title("Waktu vs Jumlah Thread")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figdir / "waktu_vs_thread.png", dpi=150)
    plt.close()

    # 2. Waktu vs Jumlah Process (mode Multiprocessing).
    mp = df[df["Mode"] == "Multiprocessing"].sort_values(["File", "Process"])
    plt.figure()
    for nf, g in mp.groupby("File"):
        plt.plot(g["Process"], g["Waktu (s)"], marker="o", label=f"{nf} file")
    plt.xlabel("Jumlah Process")
    plt.ylabel("Waktu (s)")
    plt.title("Waktu vs Jumlah Process")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figdir / "waktu_vs_process.png", dpi=150)
    plt.close()

    # 3. Speedup vs Konfigurasi (ambil file_count terbesar agar 1 batang per konfigurasi).
    biggest = df["File"].max()
    sub = df[df["File"] == biggest].copy()
    order = ["seq"] + [f"mt-{t}t" for t in sorted(sub[sub["Mode"] == "Multithread"]["Thread"].unique())] \
        + [f"mp-{p}p" for p in sorted(sub[sub["Mode"] == "Multiprocessing"]["Process"].unique())] \
        + list(sub[sub["Mode"] == "Hybrid"]["Konfigurasi"].unique())
    sub["Konfigurasi"] = pd.Categorical(sub["Konfigurasi"], categories=order, ordered=True)
    sub = sub.sort_values("Konfigurasi")
    plt.figure(figsize=(10, 4))
    plt.bar(sub["Konfigurasi"].astype(str), sub["Speedup"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Speedup")
    plt.title(f"Speedup vs Konfigurasi ({biggest} file)")
    plt.tight_layout()
    plt.savefig(figdir / "speedup_vs_konfigurasi.png", dpi=150)
    plt.close()

    # 4-5. Opsional: throughput & efisiensi.
    plt.figure(figsize=(10, 4))
    plt.bar(sub["Konfigurasi"].astype(str), sub["Throughput"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Throughput (baris/detik)")
    plt.title(f"Throughput vs Konfigurasi ({biggest} file)")
    plt.tight_layout()
    plt.savefig(figdir / "throughput_vs_konfigurasi.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.bar(sub["Konfigurasi"].astype(str), sub["Efisiensi"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Efisiensi (%)")
    plt.title(f"Efisiensi vs Konfigurasi ({biggest} file)")
    plt.tight_layout()
    plt.savefig(figdir / "efisiensi_vs_konfigurasi.png", dpi=150)
    plt.close()

    # Tabel Markdown: gabungan + A/B/C.
    md_path = Path(args.md)
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Hasil Eksperimen\n\n")
        f.write("## Tabel Gabungan\n\n")
        f.write(df.to_markdown(index=False))
        f.write("\n\n## Tabel A — Variasi Jumlah Thread (process=1)\n\n")
        f.write(df[df["Mode"].isin(["Sequential", "Multithread"])].to_markdown(index=False))
        f.write("\n\n## Tabel B — Variasi Jumlah Process (thread=1)\n\n")
        f.write(df[df["Mode"].isin(["Sequential", "Multiprocessing"])].to_markdown(index=False))
        f.write("\n\n## Tabel C — Variasi Jumlah File (1p, 1t)\n\n")
        f.write(df[df["Mode"] == "Sequential"].to_markdown(index=False))
        f.write("\n")
    print(f"Grafik tersimpan di {figdir} (5 PNG). Tabel: {md_path}")


if __name__ == "__main__":
    main()
