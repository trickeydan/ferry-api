import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  base: "/static/",
  build: {
    lib: {
      entry: resolve(__dirname, 'assets', 'main.ts'), // Path to your TypeScript file
      formats: ['es'], // Choose desired module formats ('es' for ES modules, 'cjs' for CommonJS)
      fileName: (format) => `main.${format}.js`, // Output file naming
    },
      manifest: "manifest.json",
      outDir: resolve("./ferry/static"),
      rollupOptions: {
        input: {
          "main": 'assets/js/main.ts',
          "style": 'assets/scss/main.scss',
        }
      }
    }
  })