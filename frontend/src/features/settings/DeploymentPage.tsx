/**
 * Settings › Deployment (Track U U3, U-D2): how this deployment is configured, read only. The
 * capability groups lead, from `GET /capabilities`, each on or off with the setting that switches
 * it and its limits; then every setting from `GET /system`, one section per group in OPERATIONS'
 * order. A secret shows only whether it is set.
 */

import { API_URL } from "@/api/client";
import type { CapabilitiesResponse, SystemSetting } from "@/types";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { bytes, count, jobLimitItems } from "./limits";
import { useCapabilities, useSystem } from "./useSystem";

const GROUPS: { group: SystemSetting["group"]; title: string }[] = [
  { group: "runtime", title: "Runtime" },
  { group: "capabilities", title: "Capability settings" },
  { group: "limits", title: "Batch and job limits" },
  { group: "webhooks", title: "Webhook subscriptions" },
];

const SECRETS = new Set(["RDM_CURSOR_SIGNING_KEY", "CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY"]);

/** A setting's value as text: booleans as On and Off, lists joined, and nothing as None. */
function shown(value: unknown) {
  if (value === null || value === undefined) return "None";
  if (typeof value === "boolean") return value ? "On" : "Off";
  if (typeof value === "number") return count(value);
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  return String(value);
}

export function DeploymentPage() {
  const { system, error, retry } = useSystem();
  const { capabilities, error: capabilityError, retry: retryCapabilities } = useCapabilities();
  const failure = error || capabilityError;
  const signingKey = system?.settings.find((setting) => setting.name === "RDM_CURSOR_SIGNING_KEY");

  return (
    <SettingsLayout
      eyebrow="Administration"
      title="Deployment"
      description="How this deployment is configured. The values come from the engine's environment and change only when it restarts; they cannot be edited here."
    >
      <p className="settings-note">
        This browser application calls the API at <code>{API_URL}</code>, set by <code>VITE_API_URL</code> when the
        frontend is built.
      </p>
      {failure ? (
        <InlineError
          message={failure}
          onRetry={() => {
            if (capabilityError) retryCapabilities();
            if (error) retry();
          }}
        />
      ) : !system || !capabilities ? (
        <Skeleton label="Loading the deployment's settings" lines={8} />
      ) : (
        <>
          <Section
            title="Capability groups"
            description="A group's routes are registered only when it is on. These are deployment limits, not permissions."
          >
            <ul className="capability-groups">
              {capabilityGroups(capabilities).map((group) => (
                <li key={group.name}>
                  <div className="capability-group-header">
                    <strong>{group.name}</strong>
                    <StatusPill tone={group.enabled ? "success" : "neutral"}>{group.enabled ? "On" : "Off"}</StatusPill>
                    <code>{group.setting}</code>
                  </div>
                  <p className="section-description">{group.scope}</p>
                  {group.limits && <DescriptionList className="compact" items={group.limits} />}
                </li>
              ))}
            </ul>
          </Section>
          {GROUPS.map(({ group, title }) => (
            <Section key={group} title={title}>
              {group === "runtime" && signingKey?.source === "default" && (
                <Notice tone="warning" title="Cursors do not survive a restart">
                  <code>RDM_CURSOR_SIGNING_KEY</code> is not set, so each engine process signs cursors with its own key.
                  Cursors stop working when the engine restarts and differ between instances. Set it to keep them.
                </Notice>
              )}
              <SettingValues
                label={`${title} settings`}
                settings={system.settings.filter((setting) => setting.group === group)}
              />
            </Section>
          ))}
        </>
      )}
    </SettingsLayout>
  );
}

function SettingValues({ label, settings }: { label: string; settings: SystemSetting[] }) {
  return (
    <SettingsTable label={label} columns={["Setting", "Value", "Default", "Source", "What it controls"]}>
      {settings.map((setting) => {
        const secret = SECRETS.has(setting.name);
        return (
          <tr key={setting.name}>
            <th scope="row">
              <code>{setting.name}</code>
            </th>
            <td data-label="Value">
              {secret ? (setting.source === "environment" ? "Set" : "Not set") : shown(setting.value)}
            </td>
            <td data-label="Default">{secret ? "None" : shown(setting.default)}</td>
            <td data-label="Source" className="settings-source">
              {setting.source === "environment" ? "Environment" : "Default"}
            </td>
            <td data-label="What it controls">{setting.description}</td>
          </tr>
        );
      })}
    </SettingsTable>
  );
}

function capabilityGroups(capabilities: CapabilitiesResponse) {
  const delivery = capabilities.consumerSubscriptions.delivery;
  const groups: { name: string; enabled: boolean; setting: string; scope: string; limits?: DescriptionItem[] }[] = [
    {
      name: "Model administration",
      enabled: capabilities.modelAdmin.manageDrafts,
      setting: capabilities.modelAdmin.setting,
      scope: "Model drafts, compiling, installing and activating releases. Releases stay readable when it is off.",
    },
    {
      name: "Workspace administration",
      enabled: capabilities.workspaceAdmin.manageWorkspaces,
      setting: capabilities.workspaceAdmin.setting,
      scope: "Creating, renaming, retiring and deleting workspaces and choosing the default.",
    },
    {
      name: "Integration jobs",
      enabled: capabilities.integrationJobs.createJobs,
      setting: capabilities.integrationJobs.setting,
      scope: "Creating and cancelling batch jobs. Job reads stay available when it is off.",
      limits: [
        ...jobLimitItems(capabilities),
        { term: "Consumer batch resolve", value: `${count(capabilities.consumerApi.resolveMaxItems)} items` },
      ],
    },
    {
      name: "Webhook subscriptions",
      enabled: capabilities.consumerSubscriptions.manageSubscriptions,
      setting: capabilities.consumerSubscriptions.setting,
      scope: "Subscribing to a consumer API's events and delivering them as signed webhooks.",
      limits: [
        { term: "Allowed hosts", value: capabilities.consumerSubscriptions.allowedHosts.join(", ") || "None" },
        { term: "Delivery batch", value: `${count(delivery.maxEvents)} events, ${bytes(delivery.maxBytes)}` },
        { term: "Receiver timeout", value: `${count(delivery.timeoutSeconds)} seconds` },
        { term: "Retried for", value: `${count(delivery.retryHours)} hours` },
      ],
    },
  ];
  return groups;
}
