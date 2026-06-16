import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { cpSync, existsSync } from 'node:fs'
import path from 'node:path'

// Self-host Excalidraw's fonts so hand-drawn diagram rendering works fully offline
// (the portable Windows app has no internet at export time). Excalidraw fetches
// fonts at runtime from `${window.EXCALIDRAW_ASSET_PATH}fonts/...`; with the asset
// path set to "/" in index.html, that resolves to /fonts/..., served from dist/fonts.
// The fonts are NOT emitted by the bundler, so we copy them into the build output.
function copyExcalidrawFonts() {
  return {
    name: 'copy-excalidraw-fonts',
    apply: 'build',
    closeBundle() {
      const src = path.resolve('node_modules/@excalidraw/excalidraw/dist/prod/fonts')
      const dest = path.resolve('dist/fonts')
      if (existsSync(src)) {
        cpSync(src, dest, { recursive: true })
      } else {
        this.warn(`Excalidraw fonts not found at ${src}; diagram fonts will not be self-hosted.`)
      }
    },
  }
}

export default defineConfig({
  plugins: [
    react(),
    copyExcalidrawFonts(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5100',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
