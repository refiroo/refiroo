// The administer section's sidebar: groups of [slug, label] (see GROUPS in astro.config.mjs).
// Edited by the wave writing this section; one file per section so parallel waves do not clash.
export default [
  [
    "People and groups",
    [
      ["administer/people-and-groups", "About people and groups"],
      "guide/administer/add-a-person",
      "guide/administer/manage-a-group",
      "guide/administer/link-a-provider-person",
    ],
  ],
  [
    "Roles and grants",
    [
      ["administer/roles-and-grants", "About roles and grants"],
      "administer/permissions-reference",
      "guide/administer/grant-a-role",
      "guide/administer/create-a-custom-role",
      "guide/administer/narrow-a-grant-to-record-types",
    ],
  ],
  [
    "Sign-in and second factors",
    [
      ["administer/sign-in", "About sign-in"],
      "guide/administer/add-a-sign-in-provider",
      "guide/administer/require-a-second-factor",
      "guide/administer/help-someone-who-lost-a-device",
      "guide/administer/turn-off-local-sign-in",
    ],
  ],
  [
    "Clients for other systems",
    [
      ["administer/clients", "About clients"],
      "guide/administer/create-a-client",
      "guide/administer/rotate-a-client-secret",
      "guide/administer/grant-a-consumer-api-to-a-client",
    ],
  ],
  [
    "Signing keys",
    [
      ["administer/signing-keys", "About signing keys"],
      "guide/administer/rotate-signing-keys",
    ],
  ],
  [
    "Approvals",
    [
      ["administer/approval-policies", "About approval policies"],
      "guide/administer/set-an-approval-policy",
    ],
  ],
  [
    "Who changed what",
    [
      ["administer/audit", "About the audit"],
      "guide/administer/find-who-changed-something",
    ],
  ],
  [
    "Mail",
    [["administer/mail", "About mail"], "guide/administer/set-up-mail"],
  ],
  [
    "Webhooks",
    [
      ["administer/webhooks", "About the Webhooks page"],
      "guide/administer/create-a-webhook",
      "guide/administer/rotate-a-webhook-key",
      "guide/administer/find-out-why-a-webhook-paused",
    ],
  ],
  [
    "Settings pages for operators and integrators",
    [
      [
        "administer/api-reference-and-consumer-api-pages",
        "About the API reference and Consumer APIs pages",
      ],
      ["administer/jobs-and-limits", "About jobs and limits"],
      [
        "administer/deployment-pages",
        "About About, Deployment and Operations",
      ],
    ],
  ],
  [
    "AI",
    [
      ["administer/ai", "About AI settings and access"],
      "guide/administer/check-the-ai-provider",
    ],
  ],
  [
    "Agent access",
    [
      ["administer/agent-access", "About agent access"],
      "guide/administer/manage-agent-access",
    ],
  ],
];
