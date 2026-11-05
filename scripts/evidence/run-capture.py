"""Run an evidence pass over tools. Usage: run-capture.py <jobs-file.json> [model] [parallel] [capture|redraw|features|themes|renders|sharp|memory]
Each job is {"id", "name", "notes"}. A job that already wrote its pass's result file is skipped."""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
scratch = Path(os.environ["EVIDENCE_SCRATCH"])
jobs = json.loads(Path(sys.argv[1]).read_text())
model = sys.argv[2] if len(sys.argv) > 2 else "gpt-6.1-sol"
parallel = int(sys.argv[3]) if len(sys.argv) > 3 else 1
passes = {
    "capture": ("CAPTURE.md", "manifest.json", "codex.log"),
    "redraw": ("REDRAW.md", "redraw.json", "redraw.log"),
    "features": ("FEATURE-SHOTS.md", "feature-shots.json", "feature-shots.log"),
    "themes": ("THEMES.md", "themes.json", "themes.log"),
    "renders": ("RENDERS.md", "renders.json", "renders.log"),
    "sharp": ("SHARP.md", "sharp.json", "sharp.log"),
    "memory": ("MEMORY.md", "memory.json", "memory.log"),
}
brief, marker, log_name = passes[sys.argv[4] if len(sys.argv) > 4 else "capture"]
template = (repo / "evidence" / brief).read_text()


def run(job: dict) -> None:
    tool = job["id"]
    out = repo / "evidence/raw" / tool
    out.mkdir(parents=True, exist_ok=True)
    (repo / "evidence/downloads" / tool).mkdir(parents=True, exist_ok=True)
    if (out / marker).exists():
        return
    prompt = template
    for key, value in {
        "{ID}": tool, "{NAME}": job["name"], "{NOTES}": job.get("notes", "none"), "{OUT}": str(out), "{REPO}": str(repo),
        "{RESEARCH}": str(scratch / "research/out" / f"{tool}.json"), "{META}": str(scratch / "meta" / f"{tool}.json"),
    }.items():
        prompt = prompt.replace(key, value)
    command = ["codex", "exec", "-m", model, "-C", str(repo), "--skip-git-repo-check", "-s", "danger-full-access", prompt]
    for wait in (0, 120, 300):  # The model can report being at capacity for a few minutes at a time.
        time.sleep(wait)
        with (out / log_name).open("w") as log:
            try:
                done = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=2700)
                state = f"exit {done.returncode}"
            except subprocess.TimeoutExpired:
                state = "timeout"
        if (out / marker).exists() or "at capacity" not in (out / log_name).read_text(errors="ignore"):
            break
    print(tool, state, "ok" if (out / marker).exists() else f"NO-{marker}", flush=True)


with ThreadPoolExecutor(parallel) as pool:
    list(pool.map(run, jobs))
