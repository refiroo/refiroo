// The integrate section's sidebar: groups of [slug, label] (see GROUPS in astro.config.mjs).
// Edited by the wave writing this section; one file per section so parallel waves do not clash.
export default [
  [
    "Start here",
    [
      ["integrate/overview", "Integrating with refiroo"],
      ["integrate/signing-in-and-tokens", "Signing in and tokens"],
      "guide/integrate/get-a-token",
      [
        "integrate/identifiers-paging-and-errors",
        "Identifiers, paging and errors",
      ],
      ["integrate/versions-and-conflicts", "Versions and conflicts"],
      [
        "integrate/workspaces-contexts-and-models",
        "Workspaces, contexts and models",
      ],
      ["integrate/discovering-the-model", "Discovering the model"],
      ["integrate/api-reference", "The API reference"],
      ["integrate/compatibility", "Compatibility"],
      ["integrate/assistants-and-agents", "Assistants and agents"],
      "guide/integrate/connect-an-assistant",
    ],
  ],
  [
    "Reading records",
    [
      ["integrate/reading-records", "Reading records"],
      "guide/integrate/read-a-collection-completely-and-resume",
      ["integrate/business-dates", "Business dates"],
      "guide/integrate/read-as-of-a-date",
    ],
  ],
  [
    "Writing and files",
    [
      ["integrate/writing-in-bulk", "Writing in bulk"],
      "guide/integrate/submit-a-bulk-change",
      ["integrate/files-imports-and-exports", "Files, imports and exports"],
      "guide/integrate/exchange-a-supplier-file",
      ["integrate/jobs", "Jobs"],
      ["integrate/assistant-tasks", "Assistant tasks"],
    ],
  ],
  [
    "Following changes",
    [
      ["integrate/following-changes", "Following changes"],
      "guide/integrate/load-then-follow-changes",
    ],
  ],
  [
    "Consumer APIs",
    [
      ["integrate/consumer-apis", "About consumer APIs"],
      ["integrate/reading-business-objects", "Reading business objects"],
      "guide/integrate/read-through-a-consumer-api",
      ["integrate/looking-up-and-resolving", "Looking up and resolving"],
      "guide/integrate/resolve-a-file-of-codes",
      [
        "integrate/consumer-events-and-webhooks",
        "Consumer events and webhooks",
      ],
      "guide/integrate/subscribe-a-webhook-and-verify-it",
    ],
  ],
  [
    "Models, changes and access",
    [
      [
        "integrate/model-and-release-operations",
        "Model and release operations",
      ],
      "guide/integrate/move-records-between-models",
      [
        "integrate/changes-approvals-and-publication",
        "Changes, approvals and publication",
      ],
      [
        "integrate/security-model-for-integrators",
        "Security for integrators",
      ],
    ],
  ],
];
