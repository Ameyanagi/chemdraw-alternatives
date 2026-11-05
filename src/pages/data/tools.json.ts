import { features, groups, loadTools } from '../../lib/tools';

export async function GET() {
  return new Response(JSON.stringify({ groups, features, tools: await loadTools() }, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
