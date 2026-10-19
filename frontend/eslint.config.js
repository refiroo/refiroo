import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "coverage"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],

      // Relaxed in Phase 0 of docs/FRONTEND_STRUCTURE_REFACTOR.md so the linter could be installed
      // without also rewriting the code it measures. `react-hooks/refs` was cleared in Phase 4 and
      // is back at its default "error".
      //
      // `set-state-in-effect` stays a warning. The engine fetches inside effects and deliberately
      // carries no data-fetching library, so `setLoading(true)` before a request is the intended
      // pattern; the remaining ten sites are that, plus components mirroring a prop into state.
      // Promoting it means either adopting a data library or reworking those components, which is
      // a change to behavior rather than to structure.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  {
    // `useVirtualizer` (0.11 X6, D161) returns an object whose functions read its state at call
    // time, so React Compiler leaves the component that calls it unmemoised and says so. That is
    // the library's design: the scroll window reads the drawn range afresh on every render. It is
    // used in this file alone.
    files: ["src/ui/ScrollWindow.tsx"],
    rules: { "react-hooks/incompatible-library": "off" },
  },
  {
    files: ["**/*.test.{ts,tsx}", "src/test/**/*.ts"],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    files: ["src/{app,features,lib,model,routing}/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "react-aria-components",
              message: "Import the RDM-owned semantic wrapper from @/ui instead.",
            },
            {
              name: "lucide-react",
              message: "Use the accessible RDM Icon wrapper from @/ui/Icon instead.",
            },
          ],
          patterns: [
            {
              group: ["react-aria-components/*", "lucide-react/*"],
              message: "Feature modules may depend only on RDM-owned wrappers from @/ui.",
            },
          ],
        },
      ],
    },
  },
);
