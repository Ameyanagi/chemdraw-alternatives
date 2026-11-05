# Chemical Drawing Atlas

A hands-on comparison of chemical drawing software, at [atlas.reshiki.com](https://atlas.reshiki.com). Each tool draws the same three molecules, and every feature claim links to a screenshot, a manual or the source code. It also shows what each tool relies on, its license, price, size and memory use, with exact versions and dates.

**This site is biased toward ReShiki, because its maintainer also maintains [ReShiki](https://reshiki.com). Please be careful.** The [method page](https://atlas.reshiki.com/how-we-test/) explains how tools are tested and listed.

## Thank you, ChemDraw

ChemDraw has shaped how chemists draw for [40 years](https://revvitysignals.com/chemdraw-turns-40). It began in 1985 with Sally Evans, David A. Evans and Stewart Rubenstein, who set out to end the slow work of redrawing structures by hand. Much of what a chemical drawing is today, on a screen and in a journal, comes from that work. Every tool here is measured against the standard it set, which is why ChemDraw comes first.

This site is independent of Revvity Signals Software, and ChemDraw is its trademark.

## Develop

Use Node 24 (see `.nvmrc`) and Bun.

```sh
bun install
bun run dev
```

```sh
bun run check   # types and content rules
bun run build
bun run test    # generated pages and internal links
```

## How the data is made

| Path | What it holds |
| --- | --- |
| `src/data/features.json` | The feature checklist, each with a one-sentence test |
| `evidence/fixtures/` | Test molecules from PubChem, built by `scripts/evidence/make-fixtures.py` |
| `evidence/CAPTURE.md` | The brief for each hands-on run |
| `scripts/evidence/tiers.json` | Which tools are compared and which are only listed |
| `scripts/evidence/overrides.json` | Hand-written corrections applied last |
| `evidence/*.md` | The brief for each research and capture pass |
| `evidence/perf.json` | Measured startup and page size |
| `src/content/tools/*.json` | Generated records the site reads |
| `public/evidence/<tool>/` | Published drawings |

`evidence/raw/` and `evidence/downloads/` hold run output and are not committed.

Research and capture run through Codex: `scripts/evidence/run-research.py` makes one read-only job per tool, and `scripts/evidence/run-capture.py` drives each app one at a time. `scripts/evidence/merge.py` then combines the results. Hands-on results win over documentation, and it checks any exported structure against PubChem's InChIKey.

ChemDraw is published as exported drawings only, because its license restricts republishing its interface and bundled images. `scripts/check-content.mjs` enforces this and the first and second listing positions.

## Publish

The site is served by GitHub Pages at `atlas.reshiki.com`. In **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**, and set the custom domain there. A DNS `CNAME` record points `atlas` at `ameyanagi.github.io`. A push to `main` checks, builds and deploys the site, and pull requests are checked without deploying.

To deploy a fork, set `SITE_URL` and `BASE_PATH`.

## License

Original code, documentation and research notes are available under [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your option. Third-party screenshots, drawings, quoted text and product names are excluded and remain with their owners. See [LICENSE](LICENSE) for the scope.
