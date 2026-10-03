"""Multithread BUG (satu-satunya file boleh ber-bug, PRD 7.2).

# BUG DISENGAJA: race condition pada shared counter global tanpa lock.
Pendekatan reproduksi: tiap baris di-update via pola read -> modify -> write
terpisah (tmp = counter[k]; tmp += 1; counter[k] = tmp) pada dict global yang
dipakai bersama semua thread, plus sys.setswitchinterval kecil agar GIL
berpindah di tengah sekuens baca-tulis sehingga update hilang (lost update).
Tanpa lock, hasil akhir  seharusnya (berbeda dari sequential).

Catatan GIL: GIL TIDAK membuat `counter += 1` atomik secara logika untuk
pola read-modify-write terpisah — justru di sinilah race terjadi.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from src.config_loader import get_config
from src.log_parser import _IP_RE, _STATUS_RE

# BUG DISENGAJA: race condition — shared counter global tanpa lock.
_SHARED_TOTAL = [0]
_SHARED_STATUS: dict[str, int] = {}
_SHARED_IP: dict[str, int] = {}
_SHARED_KW = [0]


def _unsafe_inc_dict(d: dict, key: str) -> None:
    # BUG DISENGAJA: race condition — read, modify, write terpisah.
    # sleep(0) melepas GIL agar thread lain menyela di tengah sekuens.
    tmp = d.get(key, 0)
    time.sleep(0)
    tmp += 1
    d[key] = tmp


def _unsafe_inc_cell(cell: list) -> None:
    # BUG DISENGAJA: race condition — read, modify, write terpisah.
    tmp = cell[0]
    time.sleep(0)
    tmp += 1
    cell[0] = tmp


def _bug_worker(lines: list[str], keyword: str) -> None:
    kw = keyword.lower()
    for line in lines:
        _unsafe_inc_cell(_SHARED_TOTAL)
        m = _IP_RE.match(line)
        if m:
            _unsafe_inc_dict(_SHARED_IP, m.group(1))
        s = _STATUS_RE.search(line)
        if s:
            _unsafe_inc_dict(_SHARED_STATUS, s.group(1))
        if kw and kw in line.lower():
            _unsafe_inc_cell(_SHARED_KW)


def run_bug(files: list[Path], n_threads: int, keyword: str) -> dict:
    global _SHARED_TOTAL, _SHARED_STATUS, _SHARED_IP, _SHARED_KW
    _SHARED_TOTAL = [0]
    _SHARED_STATUS = {}
    _SHARED_IP = {}
    _SHARED_KW = [0]
    sys.setswitchinterval(1e-6)  # perkecil agar race mudah terpicu
    try:
        # Bagi beban per baris (bukan per file) agar semua thread
        # menulis ke counter global yang SAMA secara bersamaan.
        all_lines: list[str] = []
        for fp in files:
            with fp.open("r", encoding="utf-8", errors="replace") as f:
                all_lines.extend(f.read().splitlines())
        chunk = (len(all_lines) + n_threads - 1) // n_threads
        chunks = [all_lines[i * chunk:(i + 1) * chunk] for i in range(n_threads)]
        with ThreadPoolExecutor(max_workers=n_threads) as ex:
            list(ex.map(lambda c: _bug_worker(c, keyword), chunks))
    finally:
        sys.setswitchinterval(0.005)  # kembalikan default
    return {
        "total_baris": _SHARED_TOTAL[0],
        "levels": {"INFO": 0, "WARN": 0, "ERROR": 0, "DEBUG": 0},
        "status": dict(_SHARED_STATUS),
        "ip": dict(_SHARED_IP),
        "keyword": _SHARED_KW[0],
    }


def main() -> dict:
    cfg = get_config()
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(root / cfg["dataset"]["prepared_dir"] / "manifest.json"))
    ap.add_argument("--max-files", type=int, default=None)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    with Path(args.manifest).open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    names = [e["nama"] for e in manifest["files"]]
    if args.max_files:
        names = names[: args.max_files]
    files = [Path(args.manifest).parent / n for n in names]
    keyword = cfg["experiment"]["keyword"]

    print("=" * 60)
    print("PARALLEL LOG FILE ANALYZER")
    print("By FARIZAL MUZTAHIDIN (247006111044)")
    print("=" * 60)
    print("Mode        : Multithread-BUG")
    print(f"Thread      : {args.threads}")
    print("Process     : 1")
    print(f"File        : {len(files)}")
    print("=" * 60)
    t0 = time.perf_counter()
    hasil = run_bug(files, args.threads, keyword)
    dur = time.perf_counter() - t0
    print(f"Total baris (buggy) : {hasil['total_baris']}")
    print(f"Status (buggy)      : {dict(sorted(hasil['status'].items()))}")
    print(f"Waktu total : {dur:.3f} detik")
    print("=" * 60)

    log_dir = root / "results" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with (log_dir / f"run_{ts}.log").open("w", encoding="utf-8") as lf:
        lf.write(f"mode=Multithread-BUG threads={args.threads} files={len(files)} waktu={dur:.3f}\n")
    return {"hasil": hasil, "waktu": dur}


if __name__ == "__main__":
    main()
