import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

export default defineConfig({
  base: '/DatacenterNeed/',
  server: {
    fs: {
      allow: ['.', '../data/norway', '../docs'].map((path) => fileURLToPath(new URL(path, import.meta.url))),
    },
  },
})