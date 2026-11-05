# Chemical Drawing Atlas

A comparison of chemical drawing software built on hands-on testing. Each tool draws the same three molecules with default settings, and every feature mark says how we know it: tested, seen in the app, or cited from the manual. Versions, engines, sizes, startup times and APIs are recorded per tool.

Maintained by the developer of ReShiki, which is included. The site says so, and the [method page](src/pages/how-we-test.astro) explains the listing order.

## Develop

Use Node 24 (see `.nvmrc`) and Bun.

```sh
bun install
bun run dev
```

The site lives at the root of https://chemdraw-alternatives.reshiki.com. To deploy a fork elsewhere, set `SITE_URL` and `BASE_PATH`.

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
| `evidence/perf.json` | Measured startup, memory and page size |
| `src/content/tools/*.json` | Generated records the site reads |
| `public/evidence/<tool>/` | Published drawings |

`evidence/raw/` and `evidence/downloads/` hold run output and are not committed.

Research and capture run through Codex: `scripts/evidence/run-research.py` makes one read-only job per tool, and `scripts/evidence/run-capture.py` drives each app one at a time. `scripts/evidence/merge.py` then combines the results. Hands-on results win over documentation, and it checks any exported structure against PubChem's InChIKey.

ChemDraw is published as exported drawings only, because its license restricts republishing its interface and bundled images. `scripts/check-content.mjs` enforces this and the first and second listing positions.

## Publish to GitHub Pages

In **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**. A push to `main` builds and deploys the site. Pull requests are built but not deployed.

The workflow derives `site` and `base` from `GITHUB_REPOSITORY`. `SITE_URL` and `BASE_PATH` override this for a custom domain.

## License

Original source code: [MIT](LICENSE). Original editorial content and research data: [CC BY 4.0](CONTENT-LICENSE.md). Third-party software, product names, trademarks and screenshots keep their own rights. This project does not relicense linked material or imply vendor endorsement.
