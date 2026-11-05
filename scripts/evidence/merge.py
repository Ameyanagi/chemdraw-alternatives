# /// script
# requires-python = ">=3.12"
# dependencies = ["rdkit", "pillow", "playwright"]
# ///
"""Merge research records, hands-on manifests and timings into src/content/tools/*.json.

Usage: uv run scripts/evidence/merge.py <research-dir>
Hands-on results win over documentation. `ui` sightings only fill gaps.
Exports, drawing-area crops and one app window per tool are published. The ChemDraw EULA bars republishing its own images, so it has no window.
"""
import base64
import io
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")
repo = Path(__file__).resolve().parents[2]
research = Path(sys.argv[1])
raw = repo / "evidence/raw"
content = repo / "src/content/tools"
public = repo / "public/evidence"
catalog = json.loads((repo / "src/data/features.json").read_text())["features"]
feature_ids = [feature["id"] for feature in catalog]
fixtures = json.loads((repo / "evidence/fixtures/index.json").read_text())
overrides = json.loads((repo / "scripts/evidence/overrides.json").read_text())
perf = json.loads(p.read_text()) if (p := repo / "evidence/perf.json").exists() else {}
tiers = json.loads((repo / "scripts/evidence/tiers.json").read_text())
tier_of = {tool: tier for tier, tools in tiers.items() for tool in tools}
license_file = research / "library-licenses.json"
library_licenses = {
    alias: {"name": entry["name"], "license": entry["license"], "source": entry["source"]}
    for entry in (json.loads(license_file.read_text()) if license_file.exists() else [])
    for alias in [entry["name"], *entry.get("aliases", [])]
}
notices = json.loads(p.read_text()) if (p := research / "notices.json").exists() else {}
PLATFORMS = ("macos", "windows", "linux", "web", "ios", "android", "offline")
UNITS = {"": 1, "px": 1, "pt": 4 / 3, "in": 96, "mm": 96 / 25.4, "cm": 96 / 2.54}
SLUGS = {
    "p01": "chemdraw", "p20": "molsketch-desktop", "p15": "molsketch-web", "p18": "molview-org", "p19": "molview-com",
    "p116": "chemdraft-yuansu", "p118": "chemeditor-lernprogramme", "p119": "chemeditor-chemrise", "p138": "bonddraw",
}


def slugify(tool_id: str, name: str) -> str:
    plain = re.split(r"[(（/]", name)[0].lower().replace("ö", "o")
    return SLUGS.get(tool_id) or re.sub(r"[^a-z0-9]+", "-", plain).strip("-")


def trim(source: Path, target: Path) -> None:
    """Crop empty margins from an export so every drawing fills its tile the same way."""
    image = Image.open(source).convert("RGBA")
    canvas = Image.new("RGBA", image.size, "white")
    canvas.alpha_composite(image)
    flat = canvas.convert("RGB")
    box = ImageChops.difference(flat, Image.new("RGB", flat.size, "white")).getbbox()
    if box:
        flat = flat.crop(box)
    flat.thumbnail((1400, 1400))
    flat.save(target, optimize=True)


def clean_version(text: str | None) -> str | None:
    if not text or not re.search(r"\d", text):
        return None
    text = re.sub(r"^(\S+) \(\1\)$", r"\1", text.strip())
    if re.fullmatch(r"[0-9a-f]{40}", text):
        return f"commit {text[:7]}"
    return text if len(text) <= 28 else text[:27] + "…"


def svg_attr(tag: str, name: str) -> str | None:
    match = re.search(rf"""\s{name}\s*=\s*["']([^"']*)""", tag)
    return match[1] if match else None


def fit_svg(page, source: Path, target: Path) -> None:
    """Set the viewBox to the inked area so the molecule fills its tile, whatever canvas the tool exported."""
    text = source.read_text(errors="ignore")
    root = re.search(r"<svg\b[^>]*>", text)[0]
    if box := svg_attr(root, "viewBox"):
        x, y, width, height = map(float, re.split(r"[\s,]+", box.strip()))
    else:
        sizes = [re.fullmatch(r"([\d.]+)([a-z]*)", svg_attr(root, key) or "") for key in ("width", "height")]
        if not all(sizes):
            shutil.copyfile(source, target)
            return
        x, y, (width, height) = 0.0, 0.0, [float(size[1]) * UNITS.get(size[2], 1) for size in sizes]
    bare = re.sub(r"""\s(?:width|height|viewBox)\s*=\s*["'][^"']*["']""", "", root)[:-1].rstrip("/ ")
    scale = 1400 / max(width, height)
    sized = text.replace(root, f'{bare} viewBox="{x} {y} {width} {height}" width="{width * scale}" height="{height * scale}">', 1)
    encoded = base64.b64encode(sized.encode()).decode()
    page.set_viewport_size({"width": round(width * scale) + 1, "height": round(height * scale) + 1})
    page.set_content(f'<body style="margin:0;background:#fff"><img style="display:block" src="data:image/svg+xml;base64,{encoded}">')
    shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    ink = ImageChops.difference(shot, Image.new("RGB", shot.size, "white")).convert("L").point(lambda value: 255 * (value > 12))
    box = ink.getbbox()
    if not box:
        shutil.copyfile(source, target)
        return
    pad = 0.02 * max(box[2] - box[0], box[3] - box[1]) / scale
    left, top = x + box[0] / scale - pad, y + box[1] / scale - pad
    wide, tall = (box[2] - box[0]) / scale + 2 * pad, (box[3] - box[1]) / scale + 2 * pad
    target.write_text(text.replace(root, f'{bare} viewBox="{left:.2f} {top:.2f} {wide:.2f} {tall:.2f}">', 1))


def structure_check(folder: Path, fixture: str) -> str | None:
    for name in (f"{fixture}-out.mol", f"{fixture}-out.smi"):
        path = folder / name
        if not path.exists():
            continue
        mol = Chem.MolFromMolFile(str(path)) if name.endswith(".mol") else Chem.MolFromSmiles(path.read_text().split()[0])
        if mol is None:
            return "mismatch"
        key, wanted = Chem.MolToInchiKey(mol), fixtures[fixture]["inchiKey"]
        return "match" if key == wanted else "stereo" if key[:14] == wanted[:14] else "mismatch"
    return None


def publish_feature_shots(tool_id: str, slug: str, features: dict, folder: Path) -> None:
    """Attach the chosen screenshot to each confirmed feature. ChemDraw's interface is never published."""
    index = folder / "feature-shots.json"
    if tool_id == "p01" or not index.exists():
        return
    for key, shot in json.loads(index.read_text()).items():
        source = folder / shot["file"]
        if key not in features or features[key]["status"] not in ("yes", "partial") or not source.exists():
            continue
        target = public / slug / f"f-{key}.webp"
        target.parent.mkdir(parents=True, exist_ok=True)
        image = Image.open(source).convert("RGB")
        image.thumbnail((900, 900))
        image.save(target, quality=72, method=6)
        features[key]["shot"] = {"image": str(target.relative_to(repo / "public")), "caption": shot["caption"]}


def publish_canvas(tool_id: str, slug: str, captures: list[dict], folder: Path) -> str | None:
    """The main canvas as a user sees it, with paclitaxel loaded when the tool managed that."""
    windows = {capture["fixture"]: capture.get("window") for capture in captures}
    names = [windows.get("complex"), windows.get("simple"), windows.get("threed"), "initial.png", "editor-initial.png"]
    source = next((folder / name for name in names if name and (folder / name).exists()), None)
    if tool_id == "p01" or not source:
        return None
    target = public / slug / "canvas.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGB")
    image.thumbnail((1400, 1400))
    image.save(target, quality=76, method=6)
    return str(target.relative_to(repo / "public"))


def publish_theme(tool_id: str, slug: str, mode: str, folder: Path) -> str | None:
    source = folder / f"canvas-{mode}.png"
    if tool_id == "p01" or not source.exists():
        return None
    target = public / slug / f"canvas-{mode}.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGB")
    image.thumbnail((1400, 1400))
    image.save(target, quality=76, method=6)
    return str(target.relative_to(repo / "public"))


def publish_capture(page, slug: str, capture: dict, folder: Path) -> dict:
    fixture = capture["fixture"]
    structure = structure_check(folder, fixture)
    name = "threed-view.png" if fixture == "threed" else capture.get("export")
    source = folder / name if name else None
    image = None
    if (capture["result"] == "ok" or structure) and source and source.exists():
        target_dir = public / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{fixture}{source.suffix}"
        fit_svg(page, source, target) if source.suffix == ".svg" else trim(source, target)
        image = str(target.relative_to(repo / "public"))
    return {
        "fixture": fixture, "result": capture["result"] if image or capture["result"] != "ok" else "failed",
        "input": capture.get("input"), "image": image, "note": capture.get("note"), "structure": structure,
    }


shutil.rmtree(public, ignore_errors=True)  # Rebuilt in full each run, so a removed capture cannot linger.
playwright = sync_playwright().start()
browser = playwright.chromium.launch()
svg_page = browser.new_page()
records = []
for path in sorted((research / "out").glob("p*.json")):
    record = json.loads(path.read_text())
    tool_id = record["id"]
    meta_path = research / "meta" / f"{tool_id}.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    slug = slugify(tool_id, record["name"])
    features = {key: record["features"][key] for key in feature_ids if key in record.get("features", {})}
    for value in features.values():
        if value["source"] and not value["source"].startswith(("http", "help:")):
            value["source"] = None
        if value["status"] in ("yes", "partial", "no") and not value["source"]:
            value.update(status="unknown", evidence="none")  # An unsourced claim is not a claim.
        if value["status"] == "unknown":
            value["evidence"] = "none"
    if tier_of.get(tool_id) == "related":
        features = {}
    record["platforms"] = {key: bool(record["platforms"].get(key)) for key in PLATFORMS}
    record["price"] = {"text": record["price"].get("text") or "Not published", "source": record["price"].get("source")}
    record["license"]["kind"] = record["license"].get("kind") or "unclear"
    record["license"]["text"] = record["license"].get("text") or "Not established"
    manifest_path = raw / tool_id / "manifest.json"
    hands = None
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for key, seen in manifest.get("features", {}).items():
            if key not in feature_ids:
                continue
            base = features.get(key, {"status": "unknown", "evidence": "none", "source": None, "note": None})
            if seen["evidence"] == "tested" or base["status"] == "unknown":
                features[key] = {**base, "status": seen["status"], "evidence": seen["evidence"], "note": seen.get("note") or base["note"]}
        publish_feature_shots(tool_id, slug, features, raw / tool_id)
        hands = {
            "testedVersion": clean_version(manifest.get("testedVersion")), "testedOn": manifest["testedOn"], "platform": manifest["platform"],
            "route": manifest["route"] or "not installed", "artifact": manifest.get("artifact"), "ran": manifest["ran"] and bool(manifest.get("captures")),
            "failure": manifest.get("failure"),
            "downloadBytes": manifest.get("downloadBytes"), "installedBytes": manifest.get("installedBytes"),
            "captures": [publish_capture(svg_page, slug, c, raw / tool_id) for c in manifest.get("captures", [])],
            "canvas": publish_canvas(tool_id, slug, manifest.get("captures", []), raw / tool_id),
            "canvasLight": publish_theme(tool_id, slug, "light", raw / tool_id),
            "canvasDark": publish_theme(tool_id, slug, "dark", raw / tool_id),
            "themes": json.loads(p.read_text()) if (p := raw / tool_id / "themes.json").exists() else None,
            "memory": json.loads(p.read_text()) if (p := raw / tool_id / "memory.json").exists() else None,
            "observations": manifest.get("observations", []),
        }
    installs = record.get("install", [])
    sized = [item["bytes"] for item in sorted(installs, key=lambda item: not item.get("macArm64")) if item.get("bytes")]
    engines = json.loads(p.read_text()) if (p := research / "engines" / f"{tool_id}.json").exists() else {}
    for key, engine in (engines.get("features") or {}).items():
        if key in features and features[key]["status"] in ("yes", "partial") and engine.get("library"):
            features[key]["engine"] = {"library": engine["library"], "source": engine.get("source")}
    stack = json.loads(p.read_text()) if (p := research / "stack" / f"{tool_id}.json").exists() else {}
    built = json.loads(p.read_text()) if (p := research / "built" / f"{tool_id}.json").exists() else None
    if stack.get("languages"):
        record["languages"] = stack["languages"]
    linked = dict.fromkeys(filter(None, [(built or {}).get("editor"), *((built or {}).get("libraries") or [])]))
    github = meta.get("github")
    if release := (github or {}).get("release"):  # The API outranks research, which goes stale on fast-moving projects.
        tag = release["tag"]
        record["version"] = {"name": tag, "date": release["publishedAt"][:10], "source": f"https://github.com/{meta['repo']}/releases/tag/{tag}"}
    tool = {
        "id": tool_id, "slug": slug, "name": record["name"], "rank": 999,
        "tier": tier_of.get(tool_id) or record["tierCheck"]["proposed"], "tierReason": record["tierCheck"]["reason"],
        "summary": record["summary"], "website": record["website"], "repo": record["repo"], "docs": record["docs"], "vendor": record["vendor"],
        "license": record["license"], "price": record["price"], "platforms": record["platforms"], "version": record["version"],
        "engine": record["engine"], "languages": record["languages"], "features": features, "caveats": record["caveats"],
        "github": github and {"stars": github["stars"], "pushedAt": github["pushedAt"], "archived": github["archived"]},
        "hands": hands, "perf": perf.get(tool_id), "downloadBytes": (hands or {}).get("downloadBytes") or (sized[0] if sized else None),
        "references": meta.get("sources", []),
        "builtOn": built,
        "renderer": engines.get("renderer"), "otherLanguages": engines.get("otherLanguages"), "enginesChecked": bool(engines),
        "languageNote": stack.get("languageNote"),
        "thirdParty": {
            "summary": stack.get("thirdParty"), "source": stack.get("thirdPartySource"), "notice": notices.get(tool_id),
            "libraries": list({item["name"]: item for name in linked if (item := library_licenses.get(name))}.values()),
        },
    }
    extra = overrides.get(tool_id, {})
    for key, patch in extra.get("features", {}).items():
        tool["features"][key].update(patch)
    records.append({**tool, **{k: v for k, v in extra.items() if k != "features"}, "thirdParty": {**tool["thirdParty"], **extra.get("thirdParty", {})}})
browser.close()
playwright.stop()


def order(tool: dict) -> tuple:
    confirmed = sum(value["status"] in ("yes", "partial") for value in tool["features"].values())
    pinned = {"p01": 0, "p02": 1}.get(tool["id"], 2)
    return pinned, not (tool["hands"] and tool["hands"]["ran"]), -confirmed, tool["name"].lower()


content.mkdir(parents=True, exist_ok=True)
for stale in content.glob("*.json"):
    stale.unlink()
for rank, tool in enumerate(sorted(records, key=order), start=1):
    tool["rank"] = rank
    (content / f"{tool['slug']}.json").write_text(json.dumps(tool, indent=2, ensure_ascii=False) + "\n")
slugs = [tool["slug"] for tool in records]
assert len(slugs) == len(set(slugs)), "duplicate slugs"
print(len(records), "tools written;", sum(bool(t["hands"]) for t in records), "with hands-on results")
