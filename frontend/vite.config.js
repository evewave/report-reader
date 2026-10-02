import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 前后端分离：dev 阶段 /api 代理到本机 FastAPI(127.0.0.1:8000)，避免 CORS 与写死地址。
// 生产 build 后由 FastAPI 直接托管 dist，仍是同源 /api。
const BACKEND = process.env.RR_BACKEND || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
    },
  },
  preview: { host: "127.0.0.1", port: 4173 },
  build: { outDir: "dist", emptyOutDir: true },
});
