/**
 * Settings › Integration › API reference (Track U U4): the sources of the reference page at `/docs/api`,
 * as it lists them: the management API, then each consumer API of the active release at its
 * contract version (V2). Each opens on its own source (`?api=<slug>`) and links its OpenAPI document.
 * The consumer sources follow the chosen workspace (`?workspace=<key>`, the default workspace
 * otherwise): the list, the links to the reference page and the OpenAPI documents.
 */

import { useCallback } from "react";
import { API_URL } from "@/api/client";
import { downloadFrom } from "@/api/download";
import type { SettingsRoute } from "@/types";
import { DownloadLink } from "@/ui/DownloadLink";
import { InlineError } from "@/ui/InlineError";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { ReferenceWorkspace } from "./ReferenceWorkspace";
import { allConsumerApis, consumerSlug, openapiUrl, referenceUrl } from "./consumerAddresses";
import { useSettingsRead, useSystem } from "./useSystem";

export function ApiReferencePage({
  route,
  onNavigate,
}: {
  route: Extract<SettingsRoute, { page: "api-reference" }>;
  /** `replace` changes the route's workspace in place, without a history entry. */
  onNavigate: (route: SettingsRoute, replace?: boolean) => void;
}) {
  const { system, error: systemError, retry: retrySystem } = useSystem();
  const workspaceKey = route.workspaceKey ?? "";
  const load = useCallback(() => allConsumerApis(workspaceKey), [workspaceKey]);
  const { data: entries, error, retry } = useSettingsRead(load);
  const failure = systemError || error;
  return (
    <SettingsLayout
      eyebrow="Integration"
      title="API reference"
      description="The engine's interactive API reference, one source per API. It is built from the active model release when it opens."
    >
      <ReferenceWorkspace
        value={workspaceKey}
        onChange={(key) => onNavigate({ ...route, workspaceKey: key || undefined }, true)}
      />
      {failure ? (
        <InlineError
          message={failure}
          onRetry={() => {
            if (systemError) retrySystem();
            if (error) retry();
          }}
        />
      ) : !system || !entries ? (
        <Skeleton label="Loading the API reference's sources" lines={4} />
      ) : (
        <Section title="Sources">
          <SettingsTable label="API reference sources" columns={["Source", "Version", "OpenAPI document"]}>
            <tr>
              <th scope="row">
                <a href={referenceUrl("management")}>Management API</a>
              </th>
              <td data-label="Version">
                <code>{system.engine.managementApi}</code> (engine {system.engine.version})
              </td>
              <td data-label="OpenAPI document">
                <a href={`${API_URL}/openapi.json`}>openapi.json</a>
              </td>
            </tr>
            {entries.map((entry) => (
              <tr key={entry.consumerApi}>
                <th scope="row">
                  <a href={referenceUrl(consumerSlug(entry), workspaceKey)}>{entry.name}</a>
                </th>
                <td data-label="Version">
                  <code>v{entry.contractVersion}</code>
                </td>
                <td data-label="OpenAPI document">
                  <DownloadLink
                    href={openapiUrl(entry)}
                    save={() => downloadFrom(openapiUrl(entry), `${consumerSlug(entry)}-openapi.json`)}
                  >
                    openapi.json
                  </DownloadLink>
                </td>
              </tr>
            ))}
          </SettingsTable>
        </Section>
      )}
    </SettingsLayout>
  );
}
