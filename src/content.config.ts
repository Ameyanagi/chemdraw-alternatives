import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const products = defineCollection({
  loader: glob({ pattern: '*.md', base: './src/content/products' }),
  schema: z.object({
    productId: z.string().regex(/^P\d{2}$/),
    name: z.string(),
    category: z.enum(['Baseline', 'Desktop & web apps', 'Web editors', 'Libraries & integrations', 'Automation & utilities', 'Legacy & unconfirmed']),
    categoryOriginal: z.string(),
    platform: z.string(),
    license: z.string(),
    pricing: z.string(),
    summary: z.string(),
    caveats: z.string(),
    checked: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    evidence: z.literal('Source review'),
    sources: z.array(z.url()).min(1),
  }),
});
const guides = defineCollection({
  loader: glob({ pattern: '*.{md,mdx}', base: './src/content/guides' }),
  schema: z.object({ title: z.string(), description: z.string() }),
});
export const collections = { products, guides };
