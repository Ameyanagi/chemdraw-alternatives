import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const files=(await fs.readdir('src/content/products')).filter(f=>f.endsWith('.md'));
assert.equal(files.length,66,'The demo migration should preserve all 66 entries. Update this baseline intentionally when adding a product.');
const ids=new Set();
for(const file of files){
 const content=await fs.readFile(`src/content/products/${file}`,'utf8');
 const id=JSON.parse(content.match(/^productId: (.+)$/m)?.[1]??'null');
 assert(id&&!ids.has(id),`Missing or duplicate product ID in ${file}`);ids.add(id);
 assert(content.includes('evidence: "Source review"'),`Evidence level missing: ${file}`);
 assert(content.includes('checked: '),`Review date missing: ${file}`);
 const sources=JSON.parse(content.match(/^sources: (.+)$/m)?.[1]??'[]');
 assert(sources.length>0,`References missing: ${file}`);
 for(const url of sources)assert.equal(new URL(url).protocol,'https:',`Use HTTPS references: ${file}`);
}
console.log(`Content checks passed: ${files.length} entries with unique IDs, evidence labels, dates and HTTPS references.`);
