import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // base: '/static/' tells Vite to prefix all asset URLs with /static/ so
  // the compiled index.html references <script src="/static/assets/index-xxx.js">
  // which matches where WhiteNoise serves collected static files in Django.
  // Without this, assets are at /assets/... but Django serves them at
  // /static/assets/... → both JS and CSS return 404 → blank white page.
  base: '/static/',
})
