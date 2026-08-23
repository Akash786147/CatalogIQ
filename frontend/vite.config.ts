import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// The dev server proxies /api to the FastAPI backend, so the frontend never
// needs CORS config and `VITE_API_BASE` can stay empty in development.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
