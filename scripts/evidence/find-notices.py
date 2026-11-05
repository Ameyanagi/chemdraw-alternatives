"""Find each repository's third-party notice file. Usage: find-notices.py <research-dir>
Writes <research-dir>/notices.json as {tool id: URL}. Only exists-in-the-repository evidence, nothing inferred."""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

root = Path(sys.argv[1])
NOTICE = re.compile(r"(^|/)(third[-_ ]?party[^/]*|thirdpartynotices[^/]*|notices?(\.\w+)?|acknowledge?ments?(\.\w+)?|credits(\.\w+)?|licenses?\.(html|json))$", re.I)
SKIP = re.compile(r"(^|/)(node_modules|vendor|dist|build|target|\.git)/", re.I)


def notice_of(path: Path) -> tuple[str, str | None]:
    meta = json.loads(path.read_text())
    repo, branch = meta.get("repo"), (meta.get("github") or {}).get("defaultBranch")
    if not repo or not branch:
        return meta["id"], None
    done = subprocess.run(["gh", "api", f"repos/{repo}/git/trees/{branch}?recursive=1"], capture_output=True, text=True)
    if done.returncode:
        return meta["id"], None
    found = [item["path"] for item in json.loads(done.stdout)["tree"] if item["type"] == "blob" and NOTICE.search(item["path"]) and not SKIP.search(item["path"])]
    best = min(found, key=lambda name: (name.count("/"), len(name)), default=None)
    return meta["id"], best and f"https://github.com/{repo}/blob/{branch}/{best}"


with ThreadPoolExecutor(8) as pool:
    results = dict(pool.map(notice_of, sorted((root / "meta").glob("p*.json"))))
(root / "notices.json").write_text(json.dumps({key: value for key, value in results.items() if value}, indent=1) + "\n")
print(sum(bool(value) for value in results.values()), "notice files in", len(results), "tools")
