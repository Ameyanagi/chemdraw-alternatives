# Chemical Drawing Atlas

A source-backed, static **Astro + Markdown/MDX** demo for comparing ChemDraw alternatives. It includes 66 directory entries, ten selected comparison profiles, 20 proposed benchmark tasks, and a primary-reference index. **No product screenshots or hands-on benchmark results are included yet.**

Maintained by the developer of ReShiki, which is included in the comparison. This relationship is disclosed on the site. Documented features do not establish runtime correctness, performance, or file compatibility.

## Develop

Use Node 24 (see `.nvmrc`).

```sh
npm ci
npm run dev
```

The local URL includes `/chemdraw-alternatives/`. To run at the domain root instead, set `BASE_PATH=/`.

```sh
npm run check
npm run build
npm test
npm run preview
```

`check` validates Astro/TypeScript and editorial invariants. `test` checks generated product pages, reference preservation, and internal links/assets under the project base path. These checks validate the website, not the chemistry software being compared.

## Edit content

- `src/content/products/pNN.md`: one source-reviewed product record. Metadata is JSON-compatible YAML; keep inline arrays for sources. Product IDs remain stable.
- `src/content/guides/*.md` and `*.mdx`: editorial prose and reusable comparison components.
- `src/components/ComparisonTable.astro`: the ten-profile demo matrix; link factual claims to the corresponding product references.
- `src/data/benchmark-plan.json`: original planned benchmark tasks; all pending.
- `src/data/additional-sources.json`: supplemental documentation.
- `/data/research.json`: generated automatically from the content collection at build time.

The original Japanese research notes are retained in the directory. English prose summarizes the workflow questions. Review dates belong to product facts, not to the website build; do not refresh them without reviewing the sources.

To add a product, create a new Markdown record with the required schema, add references and a review date, and intentionally update the expected entry count in `scripts/check-content.mjs` and `tests/site.test.mjs` and editorial scope text. A product being public or free does not establish an open-source license. Use “not established” for unanswered questions, rather than “unsupported.”

## Publish to GitHub Pages

1. Create the public repository `chemdraw-alternatives` and push this project to `main`.
2. In **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**.
3. Open **Actions → Check, build and deploy Pages**. The push to `main` builds and deploys the site; use **Run workflow** if Pages was enabled afterward.
4. Wait for both jobs to pass. The deployment URL appears in the `github-pages` environment.

The workflow derives the `site` and project `base` from `GITHUB_REPOSITORY`. For a fork or renamed repository, the Pages base updates at build time. `SITE_URL` and `BASE_PATH` can override this behavior for a custom domain. The navigation source link currently points to `Ameyanagi/chemdraw-alternatives`; update it if publishing elsewhere.

Actions use full commit pins, read-only default permissions, separate deployment permissions, a lockfile, a time limit, and PR build checks. Pull requests do not deploy. Dependabot proposes dependency/action updates; inspect and test updates before merging.

## Research and references

The source index links original documentation, repository files, author statements, and license sources used in this research. A pinned repository commit may describe unreleased behavior. Release, edition, operating system, and file exchange path must be distinguished.

Product data was reviewed on the dates recorded per entry, mainly 31 Oct–04 Nov 2026. This site was prepared 05 Nov 2026. Creating the site did not re-check every external link, price, license, or release. Do not represent this demo as an exhaustive or independently tested ranking.

Future screenshot contributions should identify the version, OS, task, capture date, publication rights, caption, and accessible alternative text. Keep editable fixtures alongside runtime findings, and do not upload confidential compounds or restricted assets.

Implementation references:

- [Astro: GitHub Pages](https://docs.astro.build/en/guides/deploy/github/)
- [Astro: Content collections](https://docs.astro.build/en/guides/content-collections/)
- [Astro: MDX](https://docs.astro.build/en/guides/integrations-guide/mdx/)

## License

Original source code: [MIT](LICENSE). Original editorial content and research data: [CC BY 4.0](CONTENT-LICENSE.md). Third-party software, source documents, product names, trademarks, and future images retain their own rights. This project does not relicense linked material or imply vendor endorsement.
