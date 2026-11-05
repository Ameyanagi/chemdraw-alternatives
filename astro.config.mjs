import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';

// GitHub Actions supplies the actual owner/repository. Local builds use the
// intended project URL; override both variables when deploying a fork.
const [owner, repo] = (process.env.GITHUB_REPOSITORY || 'Ameyanagi/chemdraw-alternatives').split('/');
export default defineConfig({
  site: process.env.SITE_URL || `https://${owner.toLowerCase()}.github.io`,
  base: process.env.BASE_PATH || (repo === `${owner.toLowerCase()}.github.io` ? '/' : `/${repo}`),
  output: 'static',
  trailingSlash: 'always',
  integrations: [mdx()],
  markdown: { syntaxHighlight: 'shiki' },
});
