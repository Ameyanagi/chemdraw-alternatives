"""Time app launches. Only processes started here are stopped, so the user's own copies are safe.

Usage: uv run --no-project python scripts/evidence/measure-desktop.py <jobs.json>
jobs.json: {"p02": "/path/to/App.app", ...}. Results merge into evidence/perf.json.
"""
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
winid = str(repo / "evidence/bin/winid")
output = repo / "evidence/perf.json"
RUNS, TIMEOUT, SETTLE = 3, 60, 10


def pids_for(app: str) -> set[int]:
    done = subprocess.run(["pgrep", "-f", f"{app}/Contents/MacOS/"], capture_output=True, text=True)
    return {int(line) for line in done.stdout.split()}


def launch_once(app: str) -> tuple[float, float] | None:
    before = pids_for(app)
    started = time.perf_counter()
    subprocess.run(["open", "-n", app], check=True)
    deadline = started + TIMEOUT
    while time.perf_counter() < deadline:
        for pid in pids_for(app) - before:
            if subprocess.run([winid, str(pid)], capture_output=True, text=True).stdout.strip():
                launch_ms = (time.perf_counter() - started) * 1000
                time.sleep(SETTLE)
                rss = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
                subprocess.run(["kill", str(pid)])
                time.sleep(2)
                return launch_ms, int(rss or 0) / 1024
        time.sleep(0.03)
    for pid in pids_for(app) - before:
        subprocess.run(["kill", str(pid)])
    return None


results = json.loads(output.read_text()) if output.exists() else {}
for tool, app in json.loads(Path(sys.argv[1]).read_text()).items():
    runs = [run for run in (launch_once(app) for _ in range(RUNS)) if run]
    if runs:
        results[tool] = {
            "kind": "desktop", "launchMs": round(statistics.median(r[0] for r in runs)),
            "idleMb": round(statistics.median(r[1] for r in runs)), "loadMs": None, "transferBytes": None,
        }
    print(tool, results.get(tool), flush=True)
    output.write_text(json.dumps(results, indent=2) + "\n")
