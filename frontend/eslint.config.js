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
    files: ["**/*.test.{ts,tsx}", "src/test/**/*.ts"],
    languageOptions: { globals: { ...globals.node } },
  },
);
