import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve('dist');
const { tools, features } = JSON.parse(await fs.readFile(path.join(root, 'data/tools.json'), 'utf8'));

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  }));
  return nested.flat();
}

test('Every tool has a page that cites its sources', async () => {
  for (const tool of tools) {
    const page = await fs.readFile(path.join(root, 'tools', tool.slug, 'index.html'), 'utf8');
    assert(page.includes(tool.name.replaceAll('&', '&amp;')), tool.name);
    for (const feature of features) {
      const source = tool.features[feature.id]?.source;
      if (source?.startsWith('http')) assert(page.includes(source.replaceAll('&', '&amp;')) || page.includes(source), `${tool.name}: ${source}`);
    }
  }
});

test('Each mark leads to its proof, and each screenshot to the manual', async () => {
  const read = async (...parts) => (await fs.readFile(path.join(root, ...parts), 'utf8')).replaceAll('&#38;', '&').replaceAll('&amp;', '&');
  const compare = await read('compare/index.html');
  assert(compare.includes('data-zoom='), 'Comparison table has nothing to enlarge');
  for (const label of ['Runs on', 'Price', 'License', 'Relies on', 'Renderer', 'Main language', 'Other languages', 'Interface framework', 'Third-party licenses', 'Name to structure', 'Structure to name', 'Download size', 'Installed size', 'Memory at idle', 'Memory with paclitaxel']) assert(compare.includes(`>${label}</th>`), `Table lacks ${label}`);
  const partial = tools.filter((tool) => tool.tier !== 'related').flatMap((tool) => Object.values(tool.features)).filter((value) => value.status === 'partial');
  assert(partial.every((value) => value.note), 'A partly mark has no reason');
  assert.equal(compare.split('class="mark-reason"').length - 1, partial.length, 'Every partly mark shows its reason');
  const compared = tools.filter((item) => item.tier !== 'related');
  const handsOnShots = compared.flatMap((tool) => Object.values(tool.features)).filter((value) => value.shot && ['tested', 'ui'].includes(value.evidence));
  assert.equal(compare.split('class="mark-thumb"').length - 1, handsOnShots.length, 'Every hands-on screenshot sits in the table');
  for (const tool of compared) {
    for (const [id, value] of Object.entries(tool.features)) {
      const source = value.source?.startsWith('http') ? value.source : null;
      const handsOn = value.shot && ['tested', 'ui'].includes(value.evidence);
      if (handsOn) assert(compare.includes(`shots/${tool.slug}/${id}/`), `${tool.name} ${id}: no screenshot link`);
      else if (source && value.status !== 'unknown') assert(compare.includes(source), `${tool.name} ${id}: no manual link`);
      if (!value.shot) continue;
      const shot = await read('shots', tool.slug, id, 'index.html');
      if (source) assert(shot.includes(source), `${tool.name} ${id}: screenshot lacks manual link`);
    }
  }
});

test('Internal links and assets resolve under the project base path', async () => {
  const home = await fs.readFile(path.join(root, 'index.html'), 'utf8');
  const canonical = new URL(home.match(/rel="canonical" href="([^"]+)"/)?.[1] ?? '');
  const base = canonical.pathname.endsWith('/') ? canonical.pathname : `${canonical.pathname}/`;
  for (const file of (await walk(root)).filter((name) => name.endsWith('.html'))) {
    const html = await fs.readFile(file, 'utf8');
    assert.equal((html.match(/<h1(?:\s|>)/g) ?? []).length, 1, `Expected one h1: ${file}`);
    for (const [, link] of html.matchAll(/(?:href|src)="([^"#]+)"/g)) {
      if (!link.startsWith('/') || link.startsWith('//')) continue;
      const pathname = decodeURIComponent(new URL(link, 'https://local.test').pathname);
      assert(pathname.startsWith(base), `Link escapes project base: ${link} in ${file}`);
      const target = path.join(root, pathname.slice(base.length));
      const stat = await fs.stat(target).catch(() => null);
      assert(stat, `Missing internal target: ${link} in ${file}`);
      if (stat.isDirectory()) await fs.access(path.join(target, 'index.html'));
    }
  }
});

test('Main canvas screenshots are in the table, and ChemDraw has none', async () => {
  const compare = await fs.readFile(path.join(root, 'compare/index.html'), 'utf8');
  const withCanvas = tools.filter((tool) => tool.tier !== 'related' && tool.hands?.canvas);
  assert(withCanvas.length > 0);
  for (const tool of withCanvas) assert(compare.includes(`alt="${tool.name.replaceAll('&', '&#38;')} main canvas`), tool.name);
  assert.equal(tools.find((tool) => tool.slug === 'chemdraw').hands.canvas, null);
  for (const file of ['canvas.webp', 'canvas-light.webp', 'canvas-dark.webp']) await assert.rejects(fs.access(path.join(root, 'evidence/chemdraw', file)));
});

test('The comparison table starts with the chosen tools', async () => {
  const compare = await fs.readFile(path.join(root, 'compare/index.html'), 'utf8');
  const checked = [...compare.matchAll(/<input type="checkbox" value="([^"]+)" checked/g)].map((match) => match[1]).sort();
  assert.deepEqual(checked, ['chemdraft', 'chemdraw', 'ketcher', 'marvin-js', 'moldraw', 'octet-draw', 'reshiki']);
});

test('Ported code is never listed as a linked library', () => {
  const reshiki = tools.find((tool) => tool.slug === 'reshiki').builtOn;
  assert.deepEqual(reshiki.libraries, ['COSMolKit (Rust port of RDKit)']);
  assert(reshiki.ported.includes('RDKit'));
});

test('The table states what each tool relies on, without categories', async () => {
  const compare = await fs.readFile(path.join(root, 'compare/index.html'), 'utf8');
  const home = await fs.readFile(path.join(root, 'index.html'), 'utf8');
  assert(home.includes('Relies on Ketcher') && home.includes('Ported from RDKit, OPSIN'));
  assert(!compare.includes('class="relies"'), 'The table header stays clean; the Relies on row carries this');
  for (const label of ['Wraps Ketcher', 'Fork of', 'own editor']) assert(!compare.includes(label), label);
  assert(!compare.includes('Library not established'), 'Unchecked cells must not read as findings');
  assert.equal(tools.find((tool) => tool.slug === 'chemdraw').builtOn.libraries, null, 'RDKit is bundled in ChemDraw, but its role is undocumented');
});

test('ChemDraw is labelled as ACS style wherever defaults are claimed', async () => {
  for (const page of ['index.html', 'drawings/index.html', 'how-we-test/index.html']) {
    assert((await fs.readFile(path.join(root, page), 'utf8')).includes('ACS Document 1996'), page);
  }
});

test('OPSIN is never credited with generating names, because it only reads them', () => {
  for (const tool of tools) {
    const library = tool.features['structure-to-name']?.engine?.library ?? '';
    assert(!/^\s*OPSIN/i.test(library), `${tool.name}: ${library}`);
  }
});

test('ReShiki Python bindings are marked as nightly only', () => {
  const reshiki = tools.find((tool) => tool.slug === 'reshiki');
  assert.equal(reshiki.features['python-api'].status, 'partial');
  assert.match(reshiki.features['python-api'].note, /nightly/);
});

test('ChemDraw API marks match the edition we tested, and embedding is its own section', async () => {
  const features = tools.find((tool) => tool.slug === 'chemdraw').features;
  assert.equal(features['python-api'].status, 'partial');
  assert.equal(features.cli.status, 'no');
  const compare = await fs.readFile(path.join(root, 'compare/index.html'), 'utf8');
  assert(compare.includes('APIs and automation') && compare.includes('Embedding and extension'));
});

test('Listing order is ChemDraw, then ReShiki', () => {
  assert.deepEqual(tools.slice(0, 2).map((tool) => tool.slug), ['chemdraw', 'reshiki']);
});
