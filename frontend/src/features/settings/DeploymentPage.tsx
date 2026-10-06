/**
 * Settings › Deployment (Track U U3, U-D2): how this deployment is configured, read only. The
 * capability groups lead, from `GET /capabilities`, each on or off with the setting that switches
 * it and its limits; then every setting from `GET /system`, one section per group in OPERATIONS'
 * order. A secret shows only whether it is set.
 */

import { useEffect, useState } from "react";
import { API_URL, api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { CapabilitiesResponse, SystemSetting } from "@/types";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { useSystem } from "./useSystem";

const GROUPS: { group: SystemSetting["group"]; title: string }[] = [
  { group: "runtime", title: "Runtime" },
  { group: "capabilities", title: "Capability settings" },
  { group: "limits", title: "Batch and job limits" },
  { group: "webhooks", title: "Webhook subscriptions" },
];

const SECRETS = new Set(["RDM_CURSOR_SIGNING_KEY", "CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY"]);

const count = (value: number) => value.toLocaleString("en");
const bytes = (value: number) =>
  value >= 1024 * 1024 && value % (1024 * 1024) === 0 ? `${count(value / (1024 * 1024))} MB` : `${count(value)} bytes`;

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
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  const [capabilityError, setCapabilityError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    api
      .capabilities()
      .then((loaded) => active && setCapabilities(loaded))
      .catch((cause) => active && setCapabilityError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [attempt]);
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
            setCapabilityError("");
            setAttempt((value) => value + 1);
            retry();
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
              <SettingsTable
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

function SettingsTable({ label, settings }: { label: string; settings: SystemSetting[] }) {
  return (
    // Focusable, so a table wider than the page can be scrolled from the keyboard.
    <div className="table-wrap settings-table" role="group" aria-label={label} tabIndex={0}>
      <table>
        <thead>
          <tr>
            <th scope="col">Setting</th>
            <th scope="col">Value</th>
            <th scope="col">Default</th>
            <th scope="col">Source</th>
            <th scope="col">What it controls</th>
          </tr>
        </thead>
        <tbody>
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
        </tbody>
      </table>
    </div>
  );
}

function capabilityGroups(capabilities: CapabilitiesResponse) {
  const jobs = capabilities.integrationJobs.limits;
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
        { term: "Inline batch", value: `${count(jobs.batchMaxItems)} items, ${bytes(jobs.batchMaxBytes)}` },
        { term: "Atomic batch", value: `${count(jobs.atomicJobMaxItems)} items` },
        {
          term: "Background batch",
          value: `${count(jobs.backgroundJobMaxItems)} items, ${bytes(jobs.backgroundBatchMaxBytes)}`,
        },
        { term: "Chunk", value: `${count(jobs.chunkItems)} items` },
        { term: "Jobs kept", value: `${count(jobs.retentionDays)} days` },
        { term: "Change feed kept", value: `${count(capabilities.changeFeed.retentionDays)} days` },
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
