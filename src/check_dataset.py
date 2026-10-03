"""Validasi dataset di dataset/raw/ (read-only, TIDAK mengunduh).

- Memeriksa raw_dir ada dan berisi minimal 1 file.
- Menolak jika hanya berisi arsip (.zip/.gz/.7z/.rar/.tar).
- Menampilkan daftar file, ukuran MB, dan 5 baris pertama tiap file.
- Menyimpan metadata ke dataset/dataset_metadata.json.
- Tidak mengubah/menghapus file di dataset/raw/.
"""
import json
from pathlib import Path

from src.config_loader import get_config

ARCHIVE_SUFFIXES = {".zip", ".gz", ".7z", ".rar", ".tar"}


def check_dataset() -> dict:
    cfg = get_config()
    root = Path(__file__).resolve().parents[1]
    raw_dir = root / cfg["dataset"]["raw_dir"]

    if not raw_dir.exists():
        raise FileNotFoundError(
            f"dataset/raw/ tidak ditemukan di {raw_dir}. "
            "Ikuti Bagian 0.4 PRD: unduh manual dari Kaggle, ekstrak, "
            "lalu taruh file log di dataset/raw/."
        )

    files = sorted(p for p in raw_dir.iterdir() if p.is_file())
    if not files:
        raise FileNotFoundError(
            "dataset/raw/ kosong. Ikuti Bagian 0.4 PRD: unduh manual, "
            "ekstrak zip, lalu taruh file log di dataset/raw/."
        )

    non_archive = [p for p in files if p.suffix.lower() not in ARCHIVE_SUFFIXES]
    if not non_archive:
        raise ValueError(
            "dataset/raw/ hanya berisi arsip "
            f"{[p.name for p in files]}. Ekstrak dulu (klik kanan -> Extract All), "
            "lalu taruh file log hasil ekstrak (bukan zip) di dataset/raw/."
        )

    print("=" * 60)
    print("PARALLEL LOG FILE ANALYZER")
    print("By FARIZAL MUZTAHIDIN (247006111044)")
    print("=" * 60)
    print(f"Raw dir: {raw_dir}")
    metadata = []
    for p in non_archive:
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"\n- {p.name} : {size_mb:.2f} MB")
        try:
            with p.open("r", encoding="utf-8", errors="replace") as f:
                print("  5 baris pertama:")
                for i in range(5):
                    line = f.readline()
                    if not line:
                        break
                    print(f"    [{i + 1}] {line.rstrip()[:200]}")
        except OSError as e:
            print(f"  (gagal baca preview: {e})")
        metadata.append({"nama": p.name, "ukuran_bytes": p.stat().st_size})

    out_path = root / "dataset" / "dataset_metadata.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"files": metadata}, f, indent=2)
    print(f"\nMetadata tersimpan: {out_path}")
    return {"files": metadata, "metadata_path": str(out_path)}


if __name__ == "__main__":
    check_dataset()
