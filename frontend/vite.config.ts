import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento o Vite repassa /api para o FastAPI local; em produção o
// build é servido pelo próprio FastAPI (container único).
const apiTarget = process.env.API_TARGET ?? "http://127.0.0.1:8501";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
  },
});
