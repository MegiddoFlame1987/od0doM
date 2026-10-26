"""Zegar w GitHub Actions. Jeden przebieg żyje ok. 5 h 40 min, odpala workflowy o stałych
godzinach ET i na końcu uruchamia sam siebie (łańcuch). Cron GitHuba spóźnia się o godziny,
więc służy tylko do wznowienia łańcucha, gdy się urwie.

Zmienne: GITHUB_REPOSITORY (ustawia GitHub), HEARTBEAT_MAX_SEC (test), HEARTBEAT_DRY (test, bez gh)."""
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
REPO = os.environ.get("GITHUB_REPOSITORY", "MegiddoFlame1987/od0doM")
DRY = os.environ.get("HEARTBEAT_DRY") == "1"
MAX_RUN = int(os.environ.get("HEARTBEAT_MAX_SEC", 5 * 3600 + 40 * 60))

# (godzina ET, tolerancja spóźnienia w minutach, workflowy)
PLAN = [
    ("08:32", 45, ["forecast.yml", "forecast_v3.yml"]),   # okno prognozy do 09:20
    ("15:53", 6, ["close.yml", "close_v3.yml"]),          # okno zamknięcia do 15:59
    ("16:12", 300, ["settle.yml", "settle_v3.yml"]),      # rozliczenie, byle po 16:05
]


def dispatch(wf: str) -> None:
    cmd = ["gh", "workflow", "run", wf, "-R", REPO, "--ref", "main"]
    print(f"[{datetime.now(ET):%Y-%m-%d %H:%M} ET] dispatch {wf}", flush=True)
    if not DRY:
        subprocess.run(cmd, check=False)


def due(now: datetime, fired: set) -> list:
    """Workflowy do odpalenia teraz: cel minął, tolerancja nie, dziś jeszcze nie odpalone."""
    if now.weekday() >= 5:
        return []
    out = []
    for hm, tol, wfs in PLAN:
        key = (now.date().isoformat(), hm)
        if key in fired:
            continue
        target = datetime.combine(now.date(), datetime.strptime(hm, "%H:%M").time(), tzinfo=ET)
        if target <= now <= target + timedelta(minutes=tol):
            fired.add(key)
            out += wfs
    return out


def main(clock=None, sleep=time.sleep) -> int:
    clock = clock or (lambda: datetime.now(ET))
    start = time.time()
    fired = set()
    print(f"heartbeat start {clock():%Y-%m-%d %H:%M} ET, max {MAX_RUN}s", flush=True)
    while time.time() - start < MAX_RUN:
        for wf in due(clock(), fired):
            dispatch(wf)
        sleep(30)
    dispatch("heartbeat.yml")   # następne ogniwo łańcucha
    return 0


if __name__ == "__main__":
    sys.exit(main())
