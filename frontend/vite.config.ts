import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'react-vendor',
              test: /node_modules\/(react|react-dom|scheduler)\//,
            },
            {
              name: 'map-vendor',
              test: /node_modules\/(leaflet|react-leaflet)\//,
            },
            {
              name: 'chart-vendor',
              test: /node_modules\/(recharts|d3-[^/]+|victory-vendor)\//,
            },
            {
              name: 'icon-vendor',
              test: /node_modules\/lucide-react\//,
            },
          ],
        },
      },
    },
  },
})
