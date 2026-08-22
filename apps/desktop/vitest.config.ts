import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  ssr: {
    noExternal: ["@fluentui/react-components", "@fluentui/react-icons"],
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    deps: {
      optimizer: {
        web: {
          enabled: true,
          include: ["@fluentui/react-components"],
        },
      },
    },
  },
});
