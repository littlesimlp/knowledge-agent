import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // 显式绑定 IPv4：Vite 默认只监听 [::1]，会导致 curl 127.0.0.1 连不上，
    // 也违反本项目"所有端口只绑 127.0.0.1"的约定（D-008）
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});