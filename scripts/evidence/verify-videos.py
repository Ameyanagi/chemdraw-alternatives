# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright"]
# ///
"""Keep a video only if the tool's own page links to it and it still plays.

Usage: uv run scripts/evidence/verify-videos.py <research-dir>
Reads <research-dir>/video/*.json and writes what passes to video-ok/.
"""
import asyncio
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

research = Path(sys.argv[1])
target = research / "video-ok"
target.mkdir(exist_ok=True)
AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15"


def get(url: str, method: str = "GET", extra: dict | None = None) -> tuple[int, str, str]:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": AGENT, **(extra or {})})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = "" if method == "HEAD" else response.read(8_000_000).decode("utf-8", "ignore")
            return response.status, response.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as error:
        return error.code, "", ""
    except Exception:  # A page we cannot reach cannot confirm a video.
        return 0, "", ""


def probe(url: str) -> tuple[int, str]:
    """Some servers refuse HEAD, so fall back to asking for the first bytes."""
    status, kind, _ = get(url, "HEAD")
    if status not in (200, 206) or not kind.startswith("video"):
        status, kind, _ = get(url, "GET", {"Range": "bytes=0-1023"})
    return status, kind


def identify(url: str) -> tuple[str, str]:
    if match := re.search(r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/)|youtu\.be/)([\w-]{11})", url):
        return "youtube", match.group(1)
    if match := re.search(r"vimeo\.com/(?:video/)?(\d{6,})", url):
        return "vimeo", match.group(1)
    path = urllib.parse.urlparse(url).path
    if re.search(r"\.(mp4|webm|mov)$", path, re.I):
        return "file", path.rsplit("/", 1)[-1]
    return "link", urllib.parse.urlparse(url).path.rstrip("/") or urllib.parse.urlparse(url).netloc


def check(video: dict) -> tuple[dict | None, str]:
    if "apptrailers.itunes.apple.com" in video["url"]:  # A raw stream most browsers cannot play, so send people to the store page.
        video = {**video, "url": video["linkedFrom"], "title": "App Store preview", "poster": None}
        return {"provider": "link", "url": video["url"], "embed": None, "title": video["title"], "author": None, "linkedFrom": video["linkedFrom"], "poster": None}, "apps.apple.com"
    provider, key = identify(video["url"])
    embed = None
    if provider in ("youtube", "vimeo"):
        endpoint = "https://www.youtube.com/oembed?format=json&url=" if provider == "youtube" else "https://vimeo.com/api/oembed.json?url="
        canonical = f"https://www.youtube.com/watch?v={key}" if provider == "youtube" else f"https://vimeo.com/{key}"
        status, _, body = get(endpoint + urllib.parse.quote(canonical, safe=""))
        video = {**video, "url": canonical}
        if status == 200:
            meta = json.loads(body)
            video = {**video, "title": meta.get("title") or video["title"], "author": meta.get("author_name")}
            embed = f"https://www.youtube-nocookie.com/embed/{key}" if provider == "youtube" else f"https://player.vimeo.com/video/{key}?dnt=1"
        elif status in (401, 403):
            provider = "link"  # Public, but its owner turned embedding off.
        else:
            return None, f"video gone ({status})"
    elif provider == "file":
        status, kind = probe(video["url"])
        if status not in (200, 206) or not kind.startswith(("video", "application/octet-stream")):
            return None, f"file not playable ({status} {kind})"
    else:
        status, kind = probe(video["url"])
        if status not in (200, 206):
            return None, f"link not reachable ({status})"
        if kind.startswith("video"):
            provider = "file"
    if re.search(r"\.(mp4|webm|mov)$", video["title"], re.I):
        video = {**video, "title": "Demo video"}
    return {"provider": provider, "url": video["url"], "embed": embed, "title": video["title"], "author": video.get("author"),
            "linkedFrom": video["linkedFrom"], "poster": video.get("poster")}, key


async def main() -> None:
    found = {path.stem: json.loads(path.read_text()).get("video") for path in sorted((research / "video").glob("*.json"))}
    found = {tool: video for tool, video in found.items() if video and video.get("url") and video.get("linkedFrom")}
    for video in found.values():  # Pages may give addresses relative to themselves.
        video["url"] = urllib.parse.urljoin(video["linkedFrom"], video["url"])
        video["poster"] = video.get("poster") and urllib.parse.urljoin(video["linkedFrom"], video["poster"])
    checked = dict(zip(found, await asyncio.gather(*(asyncio.to_thread(check, video) for video in found.values()))))
    rejected = {tool: result[1] for tool, result in checked.items() if result[0] is None}
    passed = {tool: result for tool, result in checked.items() if result[0]}
    async with async_playwright() as play:
        browser = await play.chromium.launch()
        page = await browser.new_page(user_agent=AGENT)
        for tool, (video, key) in passed.items():
            source = get(video["linkedFrom"])[2]
            if key not in source:  # Pages built by scripts have no links until they run.
                try:
                    await page.goto(video["linkedFrom"], wait_until="networkidle", timeout=25000)
                    source = await page.content()
                except Exception:
                    source = ""
            if key in source:
                if video["linkedFrom"].endswith(".js"):  # People should land on the page, not its script bundle.
                    parts = urllib.parse.urlparse(video["linkedFrom"])
                    video = {**video, "linkedFrom": f"{parts.scheme}://{parts.netloc}/"}
                (target / f"{tool}.json").write_text(json.dumps(video, ensure_ascii=False, indent=1))
            else:
                rejected[tool] = f"not on {video['linkedFrom']}"
        await browser.close()
    (research / "video-rejected.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=1))
    print(f"kept {len(found) - len(rejected)}, rejected {len(rejected)}, tools without a video {len(list((research / 'video').glob('*.json'))) - len(found)}")


asyncio.run(main())
