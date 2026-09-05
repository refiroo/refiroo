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

      // Two rules are temporarily relaxed so that Phase 0 of
      // docs/FRONTEND_STRUCTURE_REFACTOR.md installs the linter without also rewriting the code it
      // measures. Both are promoted back to "error" as the exit criterion of Phase 4.
      //
      // set-state-in-effect: the engine fetches inside effects and deliberately carries no
      // data-fetching library, so `setLoading(true)` before a request is the intended pattern.
      // Phase 3 collapses the seven copies into `lib/hooks/useAsyncResource`.
      //
      // refs: one site, the return-to-collection memory in App.tsx, writes a ref during render.
      // Phase 4 moves it into `app/useRouter.ts`, where it becomes an effect.
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "src/test/**/*.ts"],
    languageOptions: { globals: { ...globals.node } },
  },
);
