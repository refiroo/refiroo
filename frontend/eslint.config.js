import { readdirSync } from "node:fs";

import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

// The import tiers of the frontend (docs/DECISIONS.md, ADR-046; docs/ARCHITECTURE.md). A feature imports
// shared state from `@/state` and shared parts from `@/ui`, `@/lib` and `@/model`, never another feature, except the
// deliberate edges listed here, each a feature that shows another feature's own part. Nothing below `app` and
// `features` imports a feature, and `state` imports only `api`, `lib`, `model`, `types` and `routing`.
const FEATURE_EDGES = {
  administration: [],
  "ai-tasks": [],
  changes: [],
  home: ["workspaces"], // the "New workspace from a workbook" action is the workspaces feature's own
  inbox: [],
  jobs: ["security"], // the job page shows its access list, the security feature's own section
  "model-admin": ["model-editor"], // a model's pages open the model editor and reuse its dialogs
  "model-editor": ["objects"], // a type's preview draws the real collection views
  moves: ["model-editor", "objects"], // a move's editor shows the editor's history; its selection uses the filter bar
  objects: [],
  security: [],
  settings: ["jobs", "security"], // Settings > Jobs and the account's access pages host those features' pages
  "sign-in": [],
  "workbook-canvas": ["model-editor", "workspaces"], // the canvas is a second view of the model editor and starts workspaces
  workspaces: ["security"], // a workspace's administration shows the access list
};
// Every feature folder is listed above, so none escapes the tiers or the wrapper rules.
const UNLISTED = readdirSync(new URL("./src/features", import.meta.url), { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && !(entry.name in FEATURE_EDGES))
  .map((entry) => entry.name);
if (UNLISTED.length) throw new Error(`List these feature folders in FEATURE_EDGES: ${UNLISTED.join(", ")}`);
const LOWER_TIERS = ["ui", "lib", "model", "api", "types", "routing", "state"];

const WRAPPER_PATHS = [
  {
    name: "react-aria-components",
    message: "Import the RDM-owned semantic wrapper from @/ui instead.",
  },
  {
    name: "lucide-react",
    message: "Use the accessible RDM Icon wrapper from @/ui/Icon instead.",
  },
];
const WRAPPER_PATTERN = {
  group: ["react-aria-components/*", "lucide-react/*"],
  message: "Feature modules may depend only on RDM-owned wrappers from @/ui.",
};

function restrictImports({ wrappers, features, extra = [] }) {
  return {
    "no-restricted-imports": [
      "error",
      {
        paths: wrappers ? WRAPPER_PATHS : [],
        patterns: [
          ...(wrappers ? [WRAPPER_PATTERN] : []),
          ...(features
            ? [
                {
                  group: ["@/features/*", ...features.map((name) => `!@/features/${name}`)],
                  message:
                    "Features import shared state from @/state and shared parts from @/ui, @/lib or @/model; a feature-to-feature import must be a deliberate edge in eslint.config.js (ADR-046).",
                },
              ]
            : []),
          ...extra,
        ],
      },
    ],
  };
}

function importTierBlocks() {
  return [
    // `app` shows the features; it only has to keep the RDM wrappers.
    { files: ["src/app/**/*.{ts,tsx}"], rules: restrictImports({ wrappers: true }) },
    ...Object.entries(FEATURE_EDGES).map(([feature, edges]) => ({
      files: [`src/features/${feature}/**/*.{ts,tsx}`],
      rules: restrictImports({ wrappers: true, features: [feature, ...edges] }),
    })),
    ...LOWER_TIERS.map((tier) => ({
      files: [`src/${tier}/**/*.{ts,tsx}`],
      rules: restrictImports({
        // `ui` is where the wrappers live, and `api`, `types` and `state` never meet them.
        wrappers: ["lib", "model", "routing"].includes(tier),
        features: [],
        extra:
          tier === "state"
            ? [
                {
                  group: ["@/ui/*", "@/app/*"],
                  message: "state imports only api, lib, model, types, routing and state.",
                },
              ]
            : [],
      }),
    })),
  ];
}

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
  ...importTierBlocks(),
);
