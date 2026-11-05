# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright"]
# ///
"""Measure uncached page load time and transfer size for hosted tools.

Usage: uv run scripts/evidence/measure-web.py <jobs.json>
jobs.json: {"p13": "https://...", ...}. Results merge into evidence/perf.json.
"""
import json
import statistics
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

output = Path(__file__).resolve().parents[2] / "evidence/perf.json"
results = json.loads(output.read_text()) if output.exists() else {}


def measure(browser, url: str) -> tuple[float, int]:
    context = browser.new_context()
    page = context.new_page()
    session = context.new_cdp_session(page)
    session.send("Network.enable")
    session.send("Network.setCacheDisabled", {"cacheDisabled": True})
    sizes: dict[str, int] = {}
    session.on("Network.loadingFinished", lambda event: sizes.__setitem__(event["requestId"], event["encodedDataLength"]))
    started = time.perf_counter()
    page.goto(url, wait_until="load", timeout=60_000)
    load_ms = (time.perf_counter() - started) * 1000
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass  # Long-polling pages never go idle; the transfer total is still valid up to here.
    context.close()
    return load_ms, sum(sizes.values())


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    for tool, url in json.loads(Path(sys.argv[1]).read_text()).items():
        try:
            runs = [measure(browser, url) for _ in range(3)]
        except Exception as error:
            print(tool, "failed:", str(error)[:120], flush=True)
            continue
        results[tool] = {
            "kind": "web", "launchMs": None, "idleMb": None,
            "loadMs": round(statistics.median(run[0] for run in runs)),
            "transferBytes": round(statistics.median(run[1] for run in runs)),
        }
        print(tool, results[tool], flush=True)
        output.write_text(json.dumps(results, indent=2) + "\n")
    browser.close()
