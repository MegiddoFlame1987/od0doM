"""Czas, ścieżki i zapis dziennego logu."""
import json
import os

import confload
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent


def data_dir() -> Path:
    d = Path(os.environ.get("DATA_DIR") or ROOT / getattr(confload.load(), "DATA_DIRNAME", "data"))
    (d / "dni").mkdir(parents=True, exist_ok=True)
    return d


def now_et() -> datetime:
    """Aktualny czas w ET. FAKE_NOW_ET (np. 2026-10-12T08:30) tylko do testów."""
    fake = os.environ.get("FAKE_NOW_ET")
    if fake:
        return datetime.fromisoformat(fake).replace(tzinfo=ET)
    return datetime.now(ET)


def in_window(t, window) -> bool:
    return window[0] <= t <= window[1]


def day_path(day: str) -> Path:
    return data_dir() / "dni" / f"{day}.json"


def load_day(day: str):
    p = day_path(day)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_day(record: dict) -> None:
    p = day_path(record["data"])
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def all_days() -> list:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((data_dir() / "dni").glob("*.json"))]


def log(msg: str) -> None:
    print(f"[{now_et():%Y-%m-%d %H:%M} ET] {msg}", flush=True)
