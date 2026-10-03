"""Mode Hybrid: ProcessPoolExecutor di atas + ThreadPoolExecutor di tiap process.

Pembagian: daftar file dibagi ke N process; di dalam tiap process,
file-file bagiannya diparsing paralel oleh T thread (local counter +
merge dua tingkat: thread -> process -> main).
Worker process HARUS di level modul agar bisa di-pickle (spawn Windows).
"""
import argparse
import json
import multiprocessing
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from src.config_loader import get_config
from src.log_parser import merge_results, parse_chunk
from src.sequential import print_footer, print_header


def _parse_one(path_str: str, keyword: str, verbose: bool = True) -> dict:
    p = Path(path_str)
    if verbose:
        tag = f"{multiprocessing.current_process().name}/{threading.current_thread().name}"
        print(f"[{tag} mulai bekerja] [MULAI] {p.name}", flush=True)
    with p.open("r", encoding="utf-8", errors="replace") as f:
        res = parse_chunk(f.read().splitlines(), keyword=keyword)
    if verbose:
        print(f"[SELESAI] {p.name}", flush=True)
    return res


def _hybrid_worker(args: tuple) -> dict:
    """Worker process: terima (list_file, threads, keyword, verbose), thread-pool internal."""
    file_strs, n_threads, keyword, verbose = args
    with ThreadPoolExecutor(max_workers=n_threads) as ex:
        parts = list(ex.map(lambda s: _parse_one(s, keyword, verbose), file_strs))
    return merge_results(parts)


def run_hybrid(files: list[Path], n_processes: int, n_threads: int, keyword: str, verbose: bool = True) -> dict:
    strs = [str(p) for p in files]
    groups: list[list[str]] = [[] for _ in range(n_processes)]
    for i, s in enumerate(strs):
        groups[i % n_processes].append(s)
    groups = [g for g in groups if g]  # buang worker menganggur jika file < process
    with ProcessPoolExecutor(max_workers=n_processes) as ex:
        partials = list(ex.map(_hybrid_worker, [(g, n_threads, keyword, verbose) for g in groups]))
    return merge_results(partials)


def main() -> dict:
    cfg = get_config()
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(root / cfg["dataset"]["prepared_dir"] / "manifest.json"))
    ap.add_argument("--max-files", type=int, default=None)
    ap.add_argument("--processes", type=int, default=2)
    ap.add_argument("--threads", type=int, default=2)
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

    print_header(len(files), n_thread=args.threads, n_process=args.processes, mode="Hybrid")
    t0 = time.perf_counter()
    hasil = run_hybrid(files, args.processes, args.threads, keyword)
    dur = time.perf_counter() - t0
    print("SEMUA ANALISIS SELESAI")

    workers = args.processes * args.threads
    throughput = hasil["total_baris"] / dur if dur > 0 else 0.0
    speedup = (args.baseline / dur) if args.baseline else 1.0
    efisiensi = speedup / workers * 100 if workers else 0.0
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
        lf.write(f"mode=Hybrid p={args.processes} t={args.threads} files={len(files)} waktu={dur:.3f}\n")
    return {"hasil": hasil, "waktu": dur}


if __name__ == "__main__":
    main()
