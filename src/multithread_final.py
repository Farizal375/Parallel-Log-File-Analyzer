"""Multithread FINAL: local counter per thread + merge (benar).

Catatan GIL: di CPython, GIL membuat thread tidak mengeksekusi
bytecode Python secara paralel untuk tugas CPU-bound. Parsing log campuran
I/O-bound (baca file) + CPU-bound (regex); thread membantu saat I/O menunggu,
tapi untuk regex berat speedup terbatas. Karena itu tiap thread memakai
counter LOKAL (tanpa shared state) lalu digabung di akhir via merge_results
— tidak ada lock, tidak ada race.
"""
import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from src.config_loader import get_config
from src.log_parser import merge_results, parse_chunk
from src.sequential import print_footer, print_header


def _parse_file(path_str: str, keyword: str, verbose: bool = True) -> dict:
    p = Path(path_str)
    if verbose:
        print(f"[{threading.current_thread().name} mulai bekerja] [MULAI] {p.name}")
    with p.open("r", encoding="utf-8", errors="replace") as f:
        res = parse_chunk(f.read().splitlines(), keyword=keyword)
    if verbose:
        print(f"[SELESAI] {p.name}")
    return res


def run_multithread(files: list[Path], n_threads: int, keyword: str, verbose: bool = True) -> dict:
    with ThreadPoolExecutor(max_workers=n_threads) as ex:
        parts = list(ex.map(lambda p: _parse_file(str(p), keyword, verbose), files))
    return merge_results(parts)


def main() -> dict:
    cfg = get_config()
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(root / cfg["dataset"]["prepared_dir"] / "manifest.json"))
    ap.add_argument("--max-files", type=int, default=None)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--baseline", type=float, default=None)
    args = ap.parse_args()

    with Path(args.manifest).open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    names = [e["nama"] for e in manifest["files"]]
    if args.max_files:
        names = names[: args.max_files]
    files = [Path(args.manifest).parent / n for n in names]
    keyword = cfg["experiment"]["keyword"]
    top_n = int(cfg["experiment"]["top_ip_count"])

    print_header(len(files), n_thread=args.threads, n_process=1, mode="Multithread")
    t0 = time.perf_counter()
    hasil = run_multithread(files, args.threads, keyword)
    dur = time.perf_counter() - t0
    print("SEMUA ANALISIS SELESAI")

    throughput = hasil["total_baris"] / dur if dur > 0 else 0.0
    speedup = (args.baseline / dur) if args.baseline else 1.0
    efisiensi = speedup / args.threads * 100 if args.threads else 0.0
    top_ips = sorted(hasil["ip"].items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    print(f"Total baris : {hasil['total_baris']}")
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
        lf.write(f"mode=Multithread threads={args.threads} files={len(files)} waktu={dur:.3f}\n")
    return {"hasil": hasil, "waktu": dur}


if __name__ == "__main__":
    main()
