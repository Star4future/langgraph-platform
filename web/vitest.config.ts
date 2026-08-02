import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  test: {
    // Reducer/selector tests run in node; component tests opt into jsdom
    // with a per-file @vitest-environment docblock.
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
