import { getCollection } from 'astro:content';
import supplemental from '../../data/additional-sources.json';
export async function GET() {
  const products = (await getCollection('products')).map(({id,data})=>({id,...data})).sort((a,b)=>a.productId.localeCompare(b.productId));
  return new Response(JSON.stringify({
    prepared:'2026-11-05',
    description:'Dated source-review snapshots. Hands-on testing pending. Entries include applications, wrappers, libraries, and utilities.',
    products, supplemental,
  }, null, 2), {headers:{'Content-Type':'application/json; charset=utf-8'}});
}
