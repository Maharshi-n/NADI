import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiUrl = process.env.VITE_API_URL || env.VITE_API_URL || 'http://localhost:8000';
  
  console.log('Vite Proxy API URL:', apiUrl);
  
  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: true,
      watch: {
        usePolling: true,
      },
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
        },
      },
    },
  };
})
