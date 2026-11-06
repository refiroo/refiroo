// The run section's sidebar: groups of [slug, label] (see GROUPS in astro.config.mjs).
// Edited by the wave writing this section; one file per section so parallel waves do not clash.
export default [
  [null, [["run/overview", "What you run"]]],
  [
    "Install",
    [
      ["run/install-with-compose", "Deploy to production with Docker"],
      ["run/developer-instance", "A developer instance"],
      ["run/database", "The database"],
      ["run/https", "Serve over HTTPS"],
      ["run/several-processes", "Several processes"],
    ],
  ],
  [
    "Configure",
    [
      ["run/configure", "Configure refiroo"],
      ["run/secrets-and-keys", "Secrets and keys"],
      ["run/sign-in-and-mail-setup", "Set up sign-in and mail"],
      ["run/ai", "About AI in refiroo"],
      "run/set-up-ai",
    ],
  ],
  [
    "Operate",
    [
      ["run/health-and-startup-checks", "Health and startup checks"],
      ["run/monitoring", "Monitor refiroo"],
      ["run/background-jobs", "Background jobs"],
      ["run/webhook-delivery", "Webhook delivery"],
      ["run/command-line", "Command-line tools"],
      ["run/troubleshooting", "Troubleshooting"],
    ],
  ],
  [
    "Maintain",
    [
      ["run/backup-and-restore", "Back up and restore"],
      ["run/upgrades", "Upgrade refiroo"],
      ["run/model-releases-and-rollback", "Model releases and rollback"],
    ],
  ],
  [
    "Before going live",
    [
      ["run/production-checklist", "Production checklist"],
      ["run/security-checklist", "Security checklist"],
    ],
  ],
  [null, [["run/licence-and-source", "Licence and source"]]],
];
