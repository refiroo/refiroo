/**
 * Settings › Integration › Consumer APIs (Track U U4): each consumer API of the chosen workspace's model release with
 * its base URL, its OpenAPI document and its routes. The API index (`GET /api/consumer`) names each one and its OpenAPI
 * document; the document gives the routes, each linked to its operation in the API reference at
 * `/docs/api`, which holds everything else the contract says. Read only: a definition changes through a
 * model release. Last, the change feed consumers follow and how long it keeps its entries (moved
 * here from Jobs and feed in 0.10 A5c). The APIs, their documents and the links to the reference
 * follow the chosen workspace (`?workspace=<key>`, the default workspace otherwise).
 */

import { useCallback } from "react";
import { api } from "@/api/client";
import { routePath } from "@/routing/routes";
import type { ConsumerApiDocument, ConsumerApiIndexEntry, SettingsRoute } from "@/types";
import { CopyValue } from "@/ui/CopyValue";
import { InlineError } from "@/ui/InlineError";
import { RouteLink } from "@/ui/RouteLink";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingRow, SettingsEmpty, SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { allConsumerApis, baseUrl, consumerSlug, openapiUrl, operationUrl } from "./consumerAddresses";
import { ReferenceWorkspace } from "./ReferenceWorkspace";
import { count } from "@/ui/limits";
import { settingsHead } from "@/ui/settingsNavigation";
import { useCapabilities, useSettingsRead } from "@/state/useSystem";

async function loadApis(workspaceKey: string) {
  const entries = await allConsumerApis(workspaceKey);
  const documents = await Promise.all(entries.map((entry) => api.consumerApiDocument(openapiUrl(entry))));
  return entries.map((entry, index) => ({ entry, document: documents[index] }));
}

/** The release the chosen workspace runs: the default workspace's is the instance's active release. */
async function loadRelease(workspaceKey: string) {
  if (!workspaceKey) {
    const { activeModelRelease } = await api.system();
    return { id: activeModelRelease.id, name: activeModelRelease.name, version: activeModelRelease.version };
  }
  const { model } = await api.workspace(workspaceKey);
  return { id: model.releaseId, name: model.releaseName, version: model.releaseVersion };
}

export function ConsumerApisPage({
  route,
  onNavigate,
}: {
  route: Extract<SettingsRoute, { page: "consumer-apis" }>;
  /** `replace` changes the route's workspace in place, without a history entry. */
  onNavigate: (route: SettingsRoute, replace?: boolean) => void;
}) {
  const workspaceKey = route.workspaceKey ?? "";
  const load = useCallback(() => loadApis(workspaceKey), [workspaceKey]);
  const { data: apis, error, retry } = useSettingsRead(load);
  const loadWorkspaceRelease = useCallback(() => loadRelease(workspaceKey), [workspaceKey]);
  const { data: release, error: releaseError, retry: retryRelease } = useSettingsRead(loadWorkspaceRelease);
  const { capabilities } = useCapabilities();
  const releaseRoute: SettingsRoute | undefined = release && { kind: "settings", page: "model", releaseId: release.id };
  const failure = error || releaseError;

  const head = settingsHead("consumer-apis");
  return (
    <SettingsLayout
      {...head}
      title="Consumer APIs"
      description="The read APIs the model release of the chosen workspace declares for consuming systems, each at its contract version, with its routes. Each route opens its documentation in the API reference."
    >
      <ReferenceWorkspace
        value={workspaceKey}
        onChange={(key) => onNavigate({ ...route, workspaceKey: key || undefined }, true)}
      />
      {failure ? (
        <InlineError
          message={failure}
          onRetry={() => {
            if (error) retry();
            if (releaseError) retryRelease();
          }}
        />
      ) : !apis || !release || !releaseRoute ? (
        <Skeleton label="Loading the consumer APIs" lines={8} />
      ) : (
        <>
          <SettingsGroup title="Model release" description="A consumer API changes only through a model release.">
            <SettingsPanel>
              <SettingRow fact name="Declared by">
                <span>
                  {release.name} {release.version}.{" "}
                  <RouteLink href={routePath(releaseRoute)} onNavigate={() => onNavigate(releaseRoute)}>
                    Open the release
                  </RouteLink>
                </span>
              </SettingRow>
            </SettingsPanel>
          </SettingsGroup>
          {apis.length === 0 ? (
            <SettingsGroup title="Consumer APIs">
              <SettingsPanel>
                <SettingsEmpty
                  icon="server"
                  hue={head.hue}
                  action={
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => onNavigate({ kind: "settings", page: "model" })}
                    >
                      Open model
                    </button>
                  }
                >
                  The workspace's model release declares no consumer API.
                </SettingsEmpty>
              </SettingsPanel>
            </SettingsGroup>
          ) : (
            apis.map(({ entry, document }) => (
              <ConsumerApi key={entry.consumerApi} entry={entry} document={document} workspaceKey={workspaceKey} />
            ))
          )}
          {capabilities && (
            <SettingsGroup
              title="Change feed"
              description={
                <>
                  Consumers follow each workspace's changes at <code>GET /api/v1/workspaces/{"{key}"}/feed</code>; a
                  position older than the retention can no longer be read.
                </>
              }
            >
              <SettingsPanel>
                <SettingRow fact name="Change feed kept">
                  {`${count(capabilities.changeFeed.retentionDays)} days`}
                </SettingRow>
              </SettingsPanel>
            </SettingsGroup>
          )}
        </>
      )}
    </SettingsLayout>
  );
}

function ConsumerApi({
  entry,
  document,
  workspaceKey,
}: {
  entry: ConsumerApiIndexEntry;
  document: ConsumerApiDocument;
  workspaceKey: string;
}) {
  const base = baseUrl(entry);
  const basePath = new URL(base).pathname;
  const slug = consumerSlug(entry);
  const documentUrl = openapiUrl(entry);
  return (
    <SettingsGroup stacked title={`${entry.name} · v${entry.contractVersion}`} description={entry.description}>
      <SettingsPanel>
        <SettingRow fact name="Base URL">
          <CopyValue label="Base URL" value={base} labelled={false} />
        </SettingRow>
        <SettingRow fact name="OpenAPI document">
          <CopyValue label="OpenAPI document" value={documentUrl} href={documentUrl} labelled={false} />
        </SettingRow>
      </SettingsPanel>
      <SettingsPanel>
        <SettingsTable label={`${entry.name}: routes`} columns={["Route", "What it does"]}>
          {Object.entries(document.paths).flatMap(([path, operations]) =>
            Object.entries(operations).map(([method, operation]) => (
              <tr key={`${method} ${path}`}>
                <th scope="row">
                  <code>
                    {method.toUpperCase()} {path.startsWith(basePath) ? path.slice(basePath.length) || "/" : path}
                  </code>
                </th>
                <td data-label="What it does">
                  <a href={operationUrl(slug, method, path, workspaceKey)}>
                    {operation.summary ?? `${method.toUpperCase()} ${path}`}
                  </a>
                </td>
              </tr>
            )),
          )}
        </SettingsTable>
      </SettingsPanel>
    </SettingsGroup>
  );
}
