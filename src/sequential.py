"""Mode Sequential: 1 proses, 1 thread, file satu per satu (baseline)."""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from src.config_loader import get_config
from src.log_parser import merge_results, parse_chunk


def print_header(n_files: int, n_thread: int = 1, n_process: int = 1, mode: str = "Sequential") -> None:
    print("=" * 60)
    print("PARALLEL LOG FILE ANALYZER")
    print("By FARIZAL MUZTAHIDIN (247006111044)")
    print("=" * 60)
    print(f"Mode        : {mode}")
    print(f"Thread      : {n_thread}")
    print(f"Process     : {n_process}")
    print(f"File        : {n_files}")
    print("=" * 60)


def print_footer() -> None:
    print("=" * 60)


def run_sequential(files: list[Path], keyword: str, top_n: int, verbose: bool = True) -> dict:
    parts = []
    for fp in files:
        if verbose:
            print(f"[MULAI] {fp.name}")
        with fp.open("r", encoding="utf-8", errors="replace") as f:
            parts.append(parse_chunk(f.read().splitlines(), keyword=keyword))
        if verbose:
            print(f"[SELESAI] {fp.name}")
    return merge_results(parts)


def main() -> dict:
    cfg = get_config()
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(root / cfg["dataset"]["prepared_dir"] / "manifest.json"))
    ap.add_argument("--max-files", type=int, default=None)
    ap.add_argument("--baseline", type=float, default=None, help="Waktu sequential acuan (untuk speedup).")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    prepared_dir = manifest_path.parent
    names = [e["nama"] for e in manifest["files"]]
    if args.max_files:
        names = names[: args.max_files]
    files = [prepared_dir / n for n in names]

    keyword = cfg["experiment"]["keyword"]
    top_n = int(cfg["experiment"]["top_ip_count"])

    print_header(len(files))
    print("Thread-1 mulai bekerja")
    t0 = time.perf_counter()
    hasil = run_sequential(files, keyword, top_n)
    dur = time.perf_counter() - t0
    print("SEMUA ANALISIS SELESAI")

    total = hasil["total_baris"]
    throughput = total / dur if dur > 0 else 0.0
    baseline = args.baseline if args.baseline else dur
    speedup = baseline / dur if dur > 0 else 0.0
    efisiensi = 100.0 if baseline == dur else speedup / 1 * 100

    top_ips = sorted(hasil["ip"].items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    print(f"Total baris : {total}")
    print(f"Levels      : {hasil['levels']} (access log -> selalu 0, bkn metrik utama)")
    print(f"Status      : {dict(sorted(hasil['status'].items()))}")
    print(f"Top {top_n} IP   : {top_ips}")
    print(f"Keyword '{keyword}': {hasil['keyword']}")
    print(f"Waktu total : {dur:.3f} detik")
    print(f"Throughput  : {throughput:.1f} baris/detik")
    print(f"Speedup     : {speedup:.2f}")
    print(f"Efisiensi   : {efisiensi:.1f}%")
    print_footer()

    log_dir = root / "results" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with (log_dir / f"run_{ts}.log").open("w", encoding="utf-8") as lf:
        lf.write(f"mode=Sequential files={len(files)} waktu={dur:.3f} throughput={throughput:.1f}\n")
    return {"hasil": hasil, "waktu": dur, "throughput": throughput}


if __name__ == "__main__":
    main()
