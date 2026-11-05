import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('dist');
const dataset=JSON.parse(await fs.readFile(path.join(root,'data/research.json'),'utf8'));
async function walk(dir){let result=[];for(const entry of await fs.readdir(dir,{withFileTypes:true})){const f=path.join(dir,entry.name);if(entry.isDirectory())result.push(...await walk(f));else result.push(f);}return result;}
test('All 66 source-backed product records have generated detail pages',async()=>{
 assert.equal(dataset.products.length,66);
 assert.equal(new Set(dataset.products.map(p=>p.productId)).size,66);
 for(const p of dataset.products){const page=await fs.readFile(path.join(root,'products',p.id,'index.html'),'utf8');assert(page.includes('Hands-on pending'));assert(page.includes(p.sources[0].replaceAll('&','&amp;'))||page.includes(p.sources[0]));}
});
test('Internal navigation and assets resolve under the GitHub Pages project base',async()=>{
 const home=await fs.readFile(path.join(root,'index.html'),'utf8');
 const canonical=new URL(home.match(/rel="canonical" href="([^"]+)"/)?.[1]??'');
 const base=canonical.pathname.endsWith('/')?canonical.pathname:canonical.pathname+'/';
 for(const file of (await walk(root)).filter(f=>f.endsWith('.html'))){
  const html=await fs.readFile(file,'utf8');
  assert.equal((html.match(/<h1(?:\s|>)/g)||[]).length,1,`Expected one page title: ${file}`);
  for(const [,link]of html.matchAll(/(?:href|src)="([^"#]+)"/g)){
   if(!link.startsWith('/')||link.startsWith('//'))continue;
   const pathname=decodeURIComponent(new URL(link,'https://local.test').pathname);
   assert(pathname.startsWith(base),`Link escapes project base: ${link} in ${file}`);
   const target=path.join(root,pathname.slice(base.length));
   const stat=await fs.stat(target).catch(()=>null);assert(stat,`Missing internal target: ${link} in ${file}`);
   if(stat.isDirectory())await fs.access(path.join(target,'index.html'));
  }
 }
});
test('Reference index includes the supporting documentation and all product sources',async()=>{
 const page=await fs.readFile(path.join(root,'references/index.html'),'utf8');
 for(const source of [...dataset.products.flatMap(p=>p.sources),...dataset.supplemental.map(s=>s.url)])assert(page.includes(source.replaceAll('&','&amp;'))||page.includes(source),`Missing source ${source}`);
});
