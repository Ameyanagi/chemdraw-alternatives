# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright"]
# ///
"""Screenshot built pages for review. Usage: shot-site.py <out-dir> [path ...] (dist must be served at BASE)."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:4399/"
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
paths = sys.argv[2:] or ["", "compare/", "under-the-hood/", "tools/reshiki/", "how-we-test/", "add/"]
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    for width, label in ((1440, "desktop"), (390, "mobile")):
        page = browser.new_context(viewport={"width": width, "height": 1000}, device_scale_factor=1).new_page()
        errors = []
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(str(error)))
        for path in paths:
            page.goto(BASE + path, wait_until="load")
            page.wait_for_timeout(500)
            name = (path.strip("/").replace("/", "-") or "home") + f"-{label}.png"
            page.screenshot(path=out / name, full_page=False)
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            print(label, path or "home", "overflowX", overflow, "errors", errors[:2])
            errors.clear()
    browser.close()
