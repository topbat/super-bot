import { resolve } from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: { lib: { entry: resolve("electron/main.ts") } },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: { lib: { entry: resolve("electron/preload.ts") } },
  },
  renderer: {
    root: ".",
    resolve: { alias: { "@renderer": resolve("src") } },
    plugins: [react()],
    build: { rollupOptions: { input: resolve("index.html") } },
  },
});
