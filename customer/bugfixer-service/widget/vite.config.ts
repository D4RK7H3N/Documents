import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: true,
    cssCodeSplit: false,
    lib: {
      entry: "src/main.ts",
      name: "BugFixerWidget",
      formats: ["iife"],
      fileName: () => "widget.js",
    },
  },
});
