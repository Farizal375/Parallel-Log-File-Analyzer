"""Split dataset log menjadi beberapa file per baris utuh + manifest.json.

- Membaca file log asli dari dataset/raw/ (streaming per baris).
- Membagi berdasarkan ukuran target MB -> dataset/prepared/.
- Menulis manifest.json berisi daftar file + jumlah baris.
- Mendukung sampling (--sample-mb) agar signature 3.3 GB bisa
  dibatasi (mis. 300 MB -> 32 file @ ~10 MB untuk file_counts).
- Default mengikuti config.yaml (file_sizes_mb), override via CLI.

Contoh (keputusan user GATE 1):
  python -m src.prepare_dataset --source access.log --sample-mb 300 --target-mb 10
"""
import argparse
import json
import time
from pathlib import Path

from src.config_loader import get_config


def split_log(
    source: Path,
    out_dir: Path,
    target_bytes: int,
    sample_bytes: int | None = None,
    prefix: str = "part",
) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Bersihkan part lama agar manifest tidak basi (hanya part_*.log).
    for old in sorted(out_dir.glob(f"{prefix}_*.log")):
        old.unlink()

    files_info: list[dict] = []
    total_written = 0
    part_idx = 1
    part_path = out_dir / f"{prefix}_{part_idx:03d}.log"
    part_bytes = 0
    part_lines = 0
    fout = part_path.open("w", encoding="utf-8", errors="replace")

    try:
        with source.open("r", encoding="utf-8", errors="replace") as fin:
            for line in fin:
                encoded = len(line.encode("utf-8", errors="replace"))
                if sample_bytes is not None and total_written + encoded > sample_bytes:
                    break
                # Jika part penuh dan sudah ada isi -> roll ke file baru.
                # Dijamin per baris utuh: roll hanya antar-baris.
                if part_lines > 0 and part_bytes + encoded > target_bytes:
                    fout.close()
                    files_info.append(
                        {"nama": part_path.name, "baris": part_lines, "bytes": part_bytes}
                    )
                    part_idx += 1
                    part_path = out_dir / f"{prefix}_{part_idx:03d}.log"
                    part_bytes = 0
                    part_lines = 0
                    fout = part_path.open("w", encoding="utf-8", errors="replace")
                fout.write(line)
                part_bytes += encoded
                part_lines += 1
                total_written += encoded
    finally:
        try:
            fout.close()
        except Exception:
            pass

    # Hapus file kosong terakhir jika ada (mis. sample tepat di batas).
    if part_lines == 0 and part_path.exists():
        part_path.unlink()
    else:
        if not any(f["nama"] == part_path.name for f in files_info):
            files_info.append(
                {"nama": part_path.name, "baris": part_lines, "bytes": part_bytes}
            )
    return files_info


def main() -> None:
    cfg = get_config()
    root = Path(__file__).resolve().parents[1]
    default_raw = root / cfg["dataset"]["raw_dir"]
    default_prepared = root / cfg["dataset"]["prepared_dir"]
    default_target_mb = cfg["dataset"]["file_sizes_mb"][0]

    ap = argparse.ArgumentParser(description="Prepare dataset log (streaming).")
    ap.add_argument("--source", default=None, help="Nama file di raw_dir (default: file log pertama)")
    ap.add_argument("--raw-dir", default=str(default_raw))
    ap.add_argument("--out-dir", default=str(default_prepared))
    ap.add_argument("--target-mb", type=float, default=float(default_target_mb))
    ap.add_argument("--sample-mb", type=float, default=None, help="Batasi total baca (MB).")
    ap.add_argument("--prefix", default="part")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    if args.source:
        source = raw_dir / args.source
    else:
        cands = sorted(
            p for p in raw_dir.iterdir()
            if p.is_file() and p.suffix.lower() not in {".zip", ".gz", ".7z", ".rar", ".tar"}
        )
        if not cands:
            raise FileNotFoundError(f"Tidak ada file log di {raw_dir}. Lihat PRD 0.4.")
        source = cands[0]

    target_bytes = int(float(args.target_mb) * 1024 * 1024)
    sample_bytes = int(float(args.sample_mb) * 1024 * 1024) if args.sample_mb else None

    print("=" * 60)
    print("PARALLEL LOG FILE ANALYZER")
    print("By FARIZAL MUZTAHIDIN (247006111044)")
    print("=" * 60)
    print(f"Source   : {source}")
    print(f"Target   : {args.target_mb} MB/file")
    print(f"Sample   : {args.sample_mb} MB" if sample_bytes else "Sample   : full")
    t0 = time.perf_counter()
    files_info = split_log(source, out_dir, target_bytes, sample_bytes, args.prefix)
    dt = time.perf_counter() - t0

    manifest = {
        "source": source.name,
        "target_mb": args.target_mb,
        "sample_mb": args.sample_mb,
        "files": files_info,
        "total_files": len(files_info),
        "total_baris": sum(f["baris"] for f in files_info),
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Hasil    : {len(files_info)} file, {manifest['total_baris']} baris, {dt:.2f}s")
    print(f"Manifest : {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
