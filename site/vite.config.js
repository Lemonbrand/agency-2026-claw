import { defineConfig } from 'vite';
import { resolve } from 'path';

const root = resolve(__dirname);

const challenges = [
  '01-zombie-recipients',
  '02-ghost-capacity',
  '03-funding-loops',
  '04-sole-source-amendment',
  '05-vendor-concentration',
  '06-related-parties',
  '07-policy-misalignment',
  '08a-duplicative-overlap',
  '08b-funding-gaps',
  '09-contract-intelligence',
  '10-adverse-media',
];

const explore = ['stories', 'sovereignty', 'audit', 'data-tables', 'ask', 'decisions'];

const inputs = {
  home: resolve(root, 'index.html'),
  stories: resolve(root, 'stories.html'),
  trust: resolve(root, 'trust.html'),
  dialogue: resolve(root, 'sovereignty-dialogue.html'),
};
for (const slug of challenges) {
  inputs[`challenge_${slug}`] = resolve(root, `challenges/${slug}.html`);
}
for (const slug of explore) {
  inputs[`explore_${slug}`] = resolve(root, `explore/${slug}.html`);
}

export default defineConfig({
  root,
  base: '/',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: { input: inputs },
    target: 'es2020',
    minify: 'esbuild',
    sourcemap: false,
  },
  server: { port: 5173, host: true, open: true },
  preview: { port: 4173, host: true },
});
