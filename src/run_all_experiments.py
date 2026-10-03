"""Otomasi benchmark: loop file_counts -> mode -> threads/processes.

- Loop paling luar file_counts (variasi jumlah file), lalu mode
  (sequential/multithread/multiprocessing/hybrid), lalu threads/processes.
  Setiap kombinasi diulang repetitions kali dan diambil median waktunya.
- Baseline speedup = median sequential pada file_count yang SAMA.
- Output: results/tables/hasil_eksperimen.csv + results/logs/run_*.log.
- Jika file_counts > file tersedia di manifest -> cap + warning.
- AGENT HANYA MENULIS SKRIP. Eksperimen final dijalankan user (PRD 11 Fase 5).
"""
import argparse
import csv
import statistics
import time
from datetime import datetime
from pathlib import Path

from src.config_loader import get_config
from src.hybrid_final import run_hybrid
from src.multiprocessing_final import run_multiprocessing
from src.multithread_final import run_multithread
from src.sequential import run_sequential


def _median(times: list[float]) -> float:
    return statistics.median(times)


def _effic(speedup: float, workers: int) -> float:
    return speedup / workers * 100 if workers else 0.0


def _unwrap(res: dict) -> dict:
    return res["hasil"] if "hasil" in res else res


def main() -> Path:
    cfg = get_config()
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(root / cfg["dataset"]["prepared_dir"] / "manifest.json"))
    ap.add_argument("--file-counts", default=",".join(map(str, cfg["experiment"]["file_counts"])))
    ap.add_argument("--threads", default=",".join(map(str, cfg["experiment"]["threads"])))
    ap.add_argument("--processes", default=",".join(map(str, cfg["experiment"]["processes"])))
    ap.add_argument("--hybrid", default=";".join(f"{h['processes']}x{h['threads']}" for h in cfg["experiment"]["hybrid_configs"]))
    ap.add_argument("--repetitions", type=int, default=int(cfg["experiment"]["repetitions"]))
    ap.add_argument("--out", default=str(root / "results" / "tables" / "hasil_eksperimen.csv"))
    args = ap.parse_args()

    file_counts = [int(x) for x in args.file_counts.split(",") if x.strip()]
    threads_list = [int(x) for x in args.threads.split(",") if x.strip()]
    procs_list = [int(x) for x in args.processes.split(",") if x.strip()]
    hybrid_cfgs = []
    for tok in args.hybrid.split(";"):
        p, t = tok.lower().replace("p", "").split("x")
        hybrid_cfgs.append((int(p), int(t)))

    manifest_path = Path(args.manifest)
    import json as _json

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = _json.load(f)
    all_names = [e["nama"] for e in manifest["files"]]
    keyword = cfg["experiment"]["keyword"]
    pre_dir = manifest_path.parent
    avail = len(all_names)
    capped = [min(n, avail) for n in file_counts]
    if capped != file_counts:
        print(f"WARNING: file_counts {file_counts} dicap ke {capped} (manifest hanya {avail} file).")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir = root / "results" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"run_{ts}.log"

    print("=" * 60)
    print("PARALLEL LOG FILE ANALYZER")
    print("By FARIZAL MUZTAHIDIN (247006111044)")
    print("=" * 60)
    print(f"Mode        : Benchmark Semua Konfigurasi")
    print(f"File        : {file_counts}")
    print(f"Repetisi    : {args.repetitions}x (median)")
    print("=" * 60)

    total_t0 = time.perf_counter()
    rows: list[dict] = []
    with log_path.open("w", encoding="utf-8") as lf:
        lf.write(f"mulai={ts} file_counts={capped} repetitions={args.repetitions}\n")
        no = 0
        for nf in capped:
            files = [pre_dir / n for n in all_names[:nf]]
            # Baseline sequential dulu untuk file_count ini.
            seq_times, seq_res = [], None
            for _ in range(args.repetitions):
                t0 = time.perf_counter()
                seq_res = run_sequential(files, keyword, 10, verbose=False)
                seq_times.append(time.perf_counter() - t0)
            base = _median(seq_times)
            total = _unwrap(seq_res)["total_baris"]
            thr = total / base if base > 0 else 0.0
            no += 1
            rows.append({"No": no, "Mode": "Sequential", "Thread": 1, "Process": 1,
                         "File": nf, "Total Baris": total, "Waktu (s)": round(base, 3),
                         "Throughput": round(thr, 1), "Speedup": 1.0, "Efisiensi": 100.0})
            lf.write(f"seq files={nf} waktu={base:.3f}\n")
            print(f"[file={nf}] Sequential: {base:.3f}s")

            for th in threads_list:
                ts_, r_ = [], None
                for _ in range(args.repetitions):
                    t0 = time.perf_counter()
                    r_ = run_multithread(files, th, keyword, verbose=False)
                    ts_.append(time.perf_counter() - t0)
                med = _median(ts_)
                tot = _unwrap(r_)["total_baris"]
                sp = base / med if med > 0 else 0.0
                no += 1
                rows.append({"No": no, "Mode": "Multithread", "Thread": th, "Process": 1,
                             "File": nf, "Total Baris": tot, "Waktu (s)": round(med, 3),
                             "Throughput": round(tot / med, 1) if med > 0 else 0.0,
                             "Speedup": round(sp, 2), "Efisiensi": round(_effic(sp, th), 1)})
                lf.write(f"mt files={nf} th={th} waktu={med:.3f} speedup={sp:.2f}\n")
                print(f"[file={nf}] Multithread th={th}: {med:.3f}s speedup={sp:.2f}")

            for pr in procs_list:
                ts_, r_ = [], None
                for _ in range(args.repetitions):
                    t0 = time.perf_counter()
                    r_ = run_multiprocessing(files, pr, keyword, verbose=False)
                    ts_.append(time.perf_counter() - t0)
                med = _median(ts_)
                tot = _unwrap(r_)["total_baris"]
                sp = base / med if med > 0 else 0.0
                no += 1
                rows.append({"No": no, "Mode": "Multiprocessing", "Thread": 1, "Process": pr,
                             "File": nf, "Total Baris": tot, "Waktu (s)": round(med, 3),
                             "Throughput": round(tot / med, 1) if med > 0 else 0.0,
                             "Speedup": round(sp, 2), "Efisiensi": round(_effic(sp, pr), 1)})
                lf.write(f"mp files={nf} pr={pr} waktu={med:.3f} speedup={sp:.2f}\n")
                print(f"[file={nf}] Multiprocessing pr={pr}: {med:.3f}s speedup={sp:.2f}")

            for (pr, th) in hybrid_cfgs:
                ts_, r_ = [], None
                for _ in range(args.repetitions):
                    t0 = time.perf_counter()
                    r_ = run_hybrid(files, pr, th, keyword, verbose=False)
                    ts_.append(time.perf_counter() - t0)
                med = _median(ts_)
                tot = _unwrap(r_)["total_baris"]
                sp = base / med if med > 0 else 0.0
                no += 1
                rows.append({"No": no, "Mode": "Hybrid", "Thread": th, "Process": pr,
                             "File": nf, "Total Baris": tot, "Waktu (s)": round(med, 3),
                             "Throughput": round(tot / med, 1) if med > 0 else 0.0,
                             "Speedup": round(sp, 2), "Efisiensi": round(_effic(sp, pr * th), 1)})
                lf.write(f"hy files={nf} p={pr} t={th} waktu={med:.3f} speedup={sp:.2f}\n")
                print(f"[file={nf}] Hybrid {pr}p x {th}t: {med:.3f}s speedup={sp:.2f}")

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    total_dur = time.perf_counter() - total_t0
    print("=" * 60)
    print("SEMUA EKSPERIMEN SELESAI")
    print("=" * 60)
    print(f"CSV tersimpan: {out_path} ({len(rows)} baris). Log: {log_path}")
    print(f"Waktu total : {total_dur:.2f} detik")
    print("=" * 60)
    return out_path


if __name__ == "__main__":
    main()
