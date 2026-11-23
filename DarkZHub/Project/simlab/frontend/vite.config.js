import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The dev server does not proxy API calls: the frontend talks to the
// Django backend directly and the backend allows this origin via CORS
// (CORS_ALLOWED_ORIGINS, default http://localhost:5173).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true, // fail loudly instead of shifting ports (breaks CORS)
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.js",
    globals: true,
    css: false,
  },
});
