"""Fetch repository facts through `gh` so versions and sizes come from the API, not from prose."""
from datetime import date
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

seed_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)


def gh(path: str):
    done = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(done.stdout) if done.returncode == 0 else None


def repo_of(sources: list[str]) -> str | None:
    for url in sources:
        if match := re.match(r"https://github\.com/([^/]+/[^/#?]+)", url):
            return match[1].removesuffix(".git")
    return None


def page_count(path: str) -> int | None:
    """How many items a list holds, from the last page number GitHub reports at one item per page."""
    done = subprocess.run(["gh", "api", "-i", path], capture_output=True, text=True)
    if done.returncode:
        return None
    last = re.search(r'[?&]page=(\d+)>; rel="last"', done.stdout.split("\r\n\r\n")[0])
    return int(last[1]) if last else 1


def history(repo: str) -> dict:
    commits = page_count(f"repos/{repo}/commits?per_page=1")
    first = gh(f"repos/{repo}/commits?per_page=1&page={commits}") if commits else None
    return {
        "commits": commits,
        "contributors": page_count(f"repos/{repo}/contributors?per_page=1&anon=1"),
        "firstCommit": first[0]["commit"]["author"]["date"][:10] if first else None,
    }


def fetch(tool: dict) -> tuple[str, str]:
    record = dict(tool, repo=repo_of(tool["sources"]))
    if repo := record["repo"]:
        info = gh(f"repos/{repo}") or {}
        release = gh(f"repos/{repo}/releases/latest")
        tags = gh(f"repos/{repo}/tags?per_page=1") or []
        record["github"] = {
            "exists": bool(info),
            "checkedOn": date.today().isoformat(),
            **(history(repo) if info else {}),
            "stars": info.get("stargazers_count"),
            "pushedAt": info.get("pushed_at"),
            "archived": info.get("archived"),
            "license": (info.get("license") or {}).get("spdx_id"),
            "defaultBranch": info.get("default_branch"),
            "languages": gh(f"repos/{repo}/languages"),
            "latestTag": tags[0]["name"] if tags else None,
            "release": release and {
                "tag": release["tag_name"],
                "publishedAt": release["published_at"],
                "assets": [{"name": a["name"], "bytes": a["size"], "url": a["browser_download_url"]} for a in release["assets"]],
            },
        }
    (out_dir / f"{tool['id']}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False))
    return tool["id"], record["repo"] or "-"


tools = json.loads(seed_path.read_text())
with ThreadPoolExecutor(8) as pool:
    results = list(pool.map(fetch, tools))
print(len(results), "written;", sum(r != "-" for _, r in results), "with GitHub repos")
