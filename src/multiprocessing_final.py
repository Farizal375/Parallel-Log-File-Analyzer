"""Mode Multiprocessing: ProcessPoolExecutor, 1 file per process.

Windows memakai spawn: worker HARUS di level modul (bisa di-pickle) dan
eksekusi pool HANYA di bawah if __name__ == "__main__" / guard fungsi main
yang dipanggil dari sana (PRD 7.1 #13).
"""
import argparse
import json
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

from src.config_loader import get_config
from src.log_parser import merge_results, parse_chunk
from src.sequential import print_footer, print_header


def _parse_file_worker(job: tuple) -> dict:
    """Worker level modul agar bisa di-pickle oleh spawn."""
    path_str, keyword, verbose = job
    p = Path(path_str)
    if verbose:
        print(f"[{multiprocessing.current_process().name} mulai bekerja] [MULAI] {p.name}", flush=True)
    with p.open("r", encoding="utf-8", errors="replace") as f:
        res = parse_chunk(f.read().splitlines(), keyword=keyword)
    if verbose:
        print(f"[SELESAI] {p.name}", flush=True)
    return res


def run_multiprocessing(files: list[Path], n_processes: int, keyword: str, verbose: bool = True) -> dict:
    jobs = [(str(p), keyword, verbose) for p in files]
    with ProcessPoolExecutor(max_workers=n_processes) as ex:
        parts = list(ex.map(_parse_file_worker, jobs))
    return merge_results(parts)


def main() -> dict:
    cfg = get_config()
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(root / cfg["dataset"]["prepared_dir"] / "manifest.json"))
    ap.add_argument("--max-files", type=int, default=None)
    ap.add_argument("--processes", type=int, default=4)
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

    print_header(len(files), n_thread=1, n_process=args.processes, mode="Multiprocessing")
    t0 = time.perf_counter()
    hasil = run_multiprocessing(files, args.processes, keyword)
    dur = time.perf_counter() - t0
    print("SEMUA ANALISIS SELESAI")

    throughput = hasil["total_baris"] / dur if dur > 0 else 0.0
    speedup = (args.baseline / dur) if args.baseline else 1.0
    efisiensi = speedup / args.processes * 100 if args.processes else 0.0
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
        lf.write(f"mode=Multiprocessing processes={args.processes} files={len(files)} waktu={dur:.3f}\n")
    return {"hasil": hasil, "waktu": dur}


if __name__ == "__main__":
    main()
