import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL(".", import.meta.url)) },
  },
  build: {
    outDir: "../spiderfoot/static/react-auth",
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: fileURLToPath(new URL("./main.tsx", import.meta.url)),
      output: {format:"iife", inlineDynamicImports:true, entryFileNames:"auth.js", assetFileNames:"auth.[ext]"},
    },
  },
});
