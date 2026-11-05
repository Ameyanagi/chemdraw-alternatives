"""Run one read-only Codex research job per tool. Usage: run-research.py <research-dir> <jobs> <id...>"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

root, jobs, ids = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3:]
template = (root / "PROMPT.md").read_text()
notes = json.loads((root / "notes.json").read_text())


def run(tool: str) -> str:
    target = root / "out" / f"{tool}.json"
    if target.exists():
        return f"{tool} skip"
    prompt = template.replace("{ID}", tool).replace("{NOTES}", notes.get(tool, "none"))
    command = ["codex", "exec", "-m", "gpt-6.1-sol", "-C", str(root), "--skip-git-repo-check",
               "-s", "workspace-write", "-c", "sandbox_workspace_write.network_access=true", prompt]
    with (root / "logs" / f"{tool}.log").open("w") as log:
        try:
            done = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=1500)
            state = f"exit {done.returncode}"
        except subprocess.TimeoutExpired:
            state = "timeout"
    print(tool, state, "ok" if target.exists() else "MISSING", flush=True)
    return tool


with ThreadPoolExecutor(jobs) as pool:
    list(pool.map(run, ids))
