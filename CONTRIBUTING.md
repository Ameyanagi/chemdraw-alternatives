# Contributing

## Suggest a tool

Use the [Add a tool](https://github.com/Ameyanagi/chemdraw-alternatives/issues/new?template=add-tool.yml) form. A website or GitHub link is all we need. If you work on the tool, please say so.

## Correct a result

Open an issue or pull request with the tool, the exact version, your operating system, and a source or steps to reproduce. Results apply to the version shown, so a newer release may legitimately differ.

Please keep these rules:

- Every claim needs a source or a hands-on check, and the real date it was checked.
- `no` means the docs or a test show the feature is absent. If nothing is known, use `unknown`, which the site shows as "Not established".
- Do not infer a license from a public repository.
- Declare any affiliation with a vendor or project.
- Do not contribute confidential or restricted material.

## Change the site

Tool pages are generated from `src/content/tools/*.json`, which `scripts/evidence/merge.py` writes. To change a result, edit its source (see the README) and re-run the merge, rather than editing generated files.

Run `bun run check` before submitting. To test generated pages, run `bun run build` and then `bun run test`.
