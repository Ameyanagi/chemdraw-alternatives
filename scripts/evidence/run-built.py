"""Run a web-research brief over tools in small batches. Usage: run-built.py <research-dir> <parallel> <id ...>
Writes one result per tool to <research-dir>/built, skipping tools that have one.
BATCH_BRIEF and BATCH_OUT select another brief and output folder."""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
root = Path(sys.argv[1]).resolve()
out = root / os.environ.get("BATCH_OUT", "built")
out.mkdir(exist_ok=True)
brief = (repo / "evidence" / os.environ.get("BATCH_BRIEF", "BUILT.md")).read_text()
todo = [tool for tool in sys.argv[3:] if not (out / f"{tool}.json").exists()]
batches = [todo[start:start + 8] for start in range(0, len(todo), 8)]


def run(batch: list[str]) -> None:
    command = ["codex", "exec", "-m", "gpt-6.1-sol", "-C", str(root), "--skip-git-repo-check", "-s", "workspace-write",
               "-c", "sandbox_workspace_write.network_access=true", brief + " ".join(batch)]
    done = subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=2700)
    print(batch[0], "exit", done.returncode, sum((out / f"{tool}.json").exists() for tool in batch), "of", len(batch), flush=True)


with ThreadPoolExecutor(int(sys.argv[2])) as pool:
    list(pool.map(run, batches))
