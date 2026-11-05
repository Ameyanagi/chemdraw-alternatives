import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// The site lives at the root of its own domain. Set both variables to deploy a fork elsewhere.
export default defineConfig({
  site: process.env.SITE_URL || 'https://chemdraw-alternatives.reshiki.com',
  base: process.env.BASE_PATH || '/',
  output: 'static',
  trailingSlash: 'always',
  vite: { plugins: [tailwindcss()] },
});
