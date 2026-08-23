import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  cacheDir: "node_modules/.vite/vitest-fluent-v2",
  plugins: [react()],
  ssr: {
    noExternal: ["@fluentui/react-components", "@fluentui/react-icons"],
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    server: {
      deps: {
        inline: [/@fluentui/],
      },
    },
    deps: {
      optimizer: {
        web: {
          enabled: true,
          include: ["@fluentui/react-icons"],
        },
      },
    },
  },
});
