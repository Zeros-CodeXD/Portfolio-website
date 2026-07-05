// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://zeros-codexd.github.io',
  base: '/Portfolio-website',
  vite: {
    plugins: [tailwindcss()],
  },
});
