import fs from 'node:fs/promises';
import assert from 'node:assert/strict';

const { features } = JSON.parse(await fs.readFile('src/data/features.json', 'utf8'));
const ids = new Set(features.map((feature) => feature.id));
const files = (await fs.readdir('src/content/tools')).filter((file) => file.endsWith('.json'));
const tools = await Promise.all(files.map(async (file) => JSON.parse(await fs.readFile(`src/content/tools/${file}`, 'utf8'))));

assert(files.length >= 66, 'A tool record was lost; removing a tool must be intentional.');
assert.equal(new Set(tools.map((tool) => tool.id)).size, tools.length, 'Duplicate tool ids');
const byRank = [...tools].sort((a, b) => a.rank - b.rank);
assert.equal(byRank[0].slug, 'chemdraw', 'ChemDraw is listed first');
assert.equal(byRank[1].slug, 'reshiki', 'ReShiki is listed second');

for (const tool of tools) {
  assert(tool.license.source, `License source missing: ${tool.name}`);
  for (const [id, value] of Object.entries(tool.features)) {
    assert(ids.has(id), `Unknown feature ${id}: ${tool.name}`);
    if (value.status !== 'unknown' && ['docs', 'source'].includes(value.evidence)) {
      assert(value.source, `A documented claim needs a source: ${tool.name} ${id}`);
    }
    if (value.evidence === 'none') assert.equal(value.status, 'unknown', `Claim without evidence: ${tool.name} ${id}`);
  }
  if (tool.id === 'p01') {
    for (const capture of tool.hands?.captures ?? []) {
      assert(!capture.image || !/window/.test(capture.image), 'ChemDraw UI screenshots must not be published');
    }
  }
}
console.log(`Content checks passed: ${tools.length} tools, ${features.length} features.`);
