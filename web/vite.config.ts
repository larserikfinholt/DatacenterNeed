import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    fs: {
      allow: ['.', '../data/norway', '../docs'].map((path) => fileURLToPath(new URL(path, import.meta.url))),
    },
  },
})