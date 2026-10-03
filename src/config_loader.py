"""Baca config.yaml — satu-satunya sumber Nama/NPM dan konfigurasi.

Aturan PRD 7.1 #8: modul lain dilarang hardcode Nama/NPM,
wajib mengambil dari config_loader (NAMA, NPM).
"""
from pathlib import Path

import yaml


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(config_path: Path | None = None) -> dict:
    root = _project_root()
    path = Path(config_path) if config_path else root / "config.yaml"
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_config = load_config()

NAMA: str = _config["project"]["nama"]
NPM: str = _config["project"]["npm"]


def get_config() -> dict:
    """Kembalikan dict konfigurasi utuh."""
    return _config


if __name__ == "__main__":
    print(f"Nama: {NAMA} ({NPM})")
    print(f"Threads: {_config['experiment']['threads']}")
    print(f"Processes: {_config['experiment']['processes']}")
    print(f"File counts: {_config['experiment']['file_counts']}")
