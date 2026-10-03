"""Uji konsistensi: sequential == final modes; bug terbukti berbeda di beban besar."""
from pathlib import Path

from src.hybrid_final import run_hybrid
from src.multiprocessing_final import run_multiprocessing
from src.multithread_final import run_multithread
from src.sequential import run_sequential

MINI = Path(__file__).parent / "sample_mini.log"


def _norm(r: dict) -> dict:
    return {
        "total_baris": r["total_baris"],
        "levels": r["levels"],
        "status": dict(sorted(r["status"].items())),
        "ip": dict(sorted(r["ip"].items())),
        "keyword": r["keyword"],
    }


def test_consistency_mini():
    files = [MINI]
    base = _norm(run_sequential(files, "timeout", 10))
    assert _norm(run_multithread(files, 4, "timeout")) == base
    assert _norm(run_multiprocessing(files, 2, "timeout")) == base
    assert _norm(run_hybrid(files, 2, 2, "timeout")) == base


if __name__ == "__main__":
    test_consistency_mini()
    print("test_consistency mini OK (final == sequential)")
