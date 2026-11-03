/**
 * Settings › Integration › Consumer APIs (Track U U4): each consumer API of the active release with
 * its base URL, its OpenAPI document and its routes. The API index (`GET /api/consumer`) names each one and its OpenAPI
 * document; the document gives the routes, each linked to its operation in the API reference at
 * `/docs/api`, which holds everything else the contract says. Read only: a definition changes through a
 * model release. Last, the change feed consumers follow and how long it keeps its entries (moved
 * here from Jobs and feed in 0.10 A5c).
 */

import { api } from "@/api/client";
import { routePath } from "@/routing/routes";
import type { ConsumerApiDocument, ConsumerApiIndexEntry, SettingsRoute } from "@/types";
import { CopyValue } from "@/ui/CopyValue";
import { DescriptionList } from "@/ui/DescriptionList";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { allConsumerApis, baseUrl, consumerSlug, openapiUrl, operationUrl } from "./consumerAddresses";
import { feedRetentionItem } from "./limits";
import { useCapabilities, useSettingsRead, useSystem } from "./useSystem";

async function loadApis() {
  const entries = await allConsumerApis();
  const documents = await Promise.all(entries.map((entry) => api.consumerApiDocument(openapiUrl(entry))));
  return entries.map((entry, index) => ({ entry, document: documents[index] }));
}

export function ConsumerApisPage({ onNavigate }: { onNavigate: (route: SettingsRoute) => void }) {
  const { data: apis, error, retry } = useSettingsRead(loadApis);
  const { system, error: systemError, retry: retrySystem } = useSystem();
  const { capabilities } = useCapabilities();
  const release = system?.activeModelRelease;
  const releaseRoute: SettingsRoute | undefined = release && { kind: "settings", page: "model", releaseId: release.id };
  const failure = error || systemError;

  return (
    <SettingsLayout
      eyebrow="Integration"
      title="Consumer APIs"
      description="The read APIs the active model release declares for consuming systems, each at its contract version, with its routes. Each route opens its documentation in the API reference."
    >
      {failure ? (
        <InlineError
          message={failure}
          onRetry={() => {
            if (error) retry();
            if (systemError) retrySystem();
          }}
        />
      ) : !apis || !release || !releaseRoute ? (
        <Skeleton label="Loading the consumer APIs" lines={8} />
      ) : (
        <>
          <p className="settings-note">
            Declared by the active model release, {release.name} {release.version}. A consumer API changes only through
            a model release.{" "}
            <RouteLink href={routePath(releaseRoute)} onNavigate={() => onNavigate(releaseRoute)}>
              Open the release
            </RouteLink>
          </p>
          {apis.length === 0 ? (
            <EmptyState
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
              The active release declares no consumer API.
            </EmptyState>
          ) : (
            apis.map(({ entry, document }) => <ConsumerApi key={entry.consumerApi} entry={entry} document={document} />)
          )}
          {capabilities && (
            <Section
              title="Change feed"
              description={
                <>
                  Consumers follow each workspace's changes at <code>GET /api/v1/workspaces/{"{key}"}/feed</code>; a
                  position older than the retention can no longer be read.
                </>
              }
            >
              <DescriptionList className="compact" items={[feedRetentionItem(capabilities)]} />
            </Section>
          )}
        </>
      )}
    </SettingsLayout>
  );
}

function ConsumerApi({ entry, document }: { entry: ConsumerApiIndexEntry; document: ConsumerApiDocument }) {
  const base = baseUrl(entry);
  const basePath = new URL(base).pathname;
  const slug = consumerSlug(entry);
  const documentUrl = openapiUrl(entry);
  return (
    <Section title={`${entry.name} · v${entry.contractVersion}`} description={entry.description}>
      <p className="consumer-api-base">
        <CopyValue label="Base URL" value={base} />
        <CopyValue label="OpenAPI document" value={documentUrl} href={documentUrl} />
      </p>
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
                <a href={operationUrl(slug, method, path)}>{operation.summary ?? `${method.toUpperCase()} ${path}`}</a>
              </td>
            </tr>
          )),
        )}
      </SettingsTable>
    </Section>
  );
}
