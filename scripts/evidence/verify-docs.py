# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright", "pypdf"]
# ///
"""Keep a documentation claim only if its quote is really on the cited page.

Usage: uv run scripts/evidence/verify-docs.py <research-dir>
Reads <research-dir>/docs/*.json and writes the claims that pass to docs-ok/.
"""
import asyncio
import html
import io
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright
from pypdf import PdfReader

research = Path(sys.argv[1])
target = research / "docs-ok"
target.mkdir(exist_ok=True)
AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15"


def normal(text: str) -> str:
    text = unicodedata.normalize("NFKC", html.unescape(text)).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[\s­​]+", " ", re.sub(r"[`*_]", "", text)).lower().strip()


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        body = response.read(30_000_000)
        kind = response.headers.get("Content-Type", "")
    if "pdf" in kind or url.lower().split("#")[0].endswith(".pdf"):
        return " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(body)).pages)
    return re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body.decode("utf-8", "ignore")))


async def main() -> None:
    claims = {path.stem: json.loads(path.read_text()) for path in sorted((research / "docs").glob("*.json"))}
    urls = {claim["source"].split("#")[0] for tool in claims.values() for claim in tool.get("features", {}).values() if claim.get("source")}
    pages: dict[str, str] = {}

    def grab(url: str) -> None:
        try:
            pages[url] = normal(fetch(url))
        except Exception:  # A page we cannot read cannot confirm a claim.
            pages[url] = ""

    await asyncio.gather(*(asyncio.to_thread(grab, url) for url in urls))

    missing = [(tool, key, claim) for tool, data in claims.items() for key, claim in data.get("features", {}).items()
               if claim.get("quote") and normal(claim["quote"]) not in pages.get(claim.get("source", "").split("#")[0], "")]
    rendered: dict[str, str] = {}
    async with async_playwright() as play:  # Pages built by scripts have no text until they run.
        browser = await play.chromium.launch()
        page = await browser.new_page(user_agent=AGENT)
        for url in sorted({claim["source"].split("#")[0] for _, _, claim in missing if claim.get("source")}):
            try:
                await page.goto(url, wait_until="networkidle", timeout=25000)
                rendered[url] = normal(await page.inner_text("body"))
            except Exception:
                rendered[url] = ""
        await browser.close()

    kept = dropped = 0
    rejected = []
    for tool, data in claims.items():
        good = {}
        for key, claim in data.get("features", {}).items():
            url, quote = claim.get("source", "").split("#")[0], normal(claim.get("quote") or "")
            if len(quote) >= 8 and (quote in pages.get(url, "") or quote in rendered.get(url, "")):
                good[key] = claim
            else:
                rejected.append({"id": tool, "feature": key, "status": claim.get("status"), "source": claim.get("source"), "quote": claim.get("quote")})
        kept, dropped = kept + len(good), dropped + len(data.get("features", {})) - len(good)
        (target / f"{tool}.json").write_text(json.dumps({"id": tool, "features": good}, ensure_ascii=False, indent=1))
    (research / "docs-rejected.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=1))
    print(f"kept {kept}, dropped {dropped}, pages {len(urls)}, unreadable {sum(not text for text in pages.values())}")


asyncio.run(main())
