import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    // Selection groups (docs/testing/EXECUTION_GUIDE.md). `unit` runs pure `.test.ts` files
    // without a DOM: jsdom setup cost ~1 s per file against ~10 ms of test time. A `.test.ts`
    // file that needs browser globals declares `// @vitest-environment jsdom`.
    projects: [
      {
        extends: true,
        // `tokens.css` is read as text by its contrast test (`?raw`), so CSS processing keeps it.
        test: { name: "unit", environment: "node", include: ["src/**/*.test.ts"], css: { include: [/tokens\.css/] } },
      },
      {
        extends: true,
        test: {
          name: "dom",
          environment: "jsdom",
          include: ["src/**/*.test.tsx"],
          setupFiles: "./src/test/setup.ts",
        },
      },
    ],
  },
});
