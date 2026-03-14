import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0', // 监听所有网络接口，支持局域网访问
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://10.179.224.182:8001', // 修改为实际的后端地址
        changeOrigin: true
      }
    }
  }
})
