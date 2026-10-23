/**
 * Settings › About (Track U U3): what this deployment runs, from `GET /system` (J31): the engine
 * and management API version, the schema languages and the active model release. The database's
 * migration revision is the operator's, on Deployment (0.12 D246).
 */

import { formatServerTime } from "@/lib/dates";
import type { SettingsRoute } from "@/types";
import { DescriptionList } from "@/ui/DescriptionList";
import { InlineError } from "@/ui/InlineError";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { Skeleton } from "@/ui/Skeleton";
import { useSystem } from "./useSystem";

export function AboutPage({ onNavigate }: { onNavigate: (route: SettingsRoute) => void }) {
  const { system, error, retry } = useSystem();
  const release = system?.activeModelRelease;
  const releaseRoute: SettingsRoute | undefined = release && { kind: "settings", page: "model", releaseId: release.id };
  return (
    <SettingsLayout eyebrow="General" title="About" description="What this deployment runs.">
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !system || !release || !releaseRoute ? (
        <Skeleton label="Loading what this deployment runs" lines={6} />
      ) : (
        <>
          <Section title="Engine">
            <DescriptionList
              items={[
                { term: "Engine version", value: system.engine.version },
                { term: "Management API", value: <code>{system.engine.managementApi}</code> },
                { term: "Schema languages", value: system.schemaLanguages.join(", ") },
              ]}
            />
          </Section>
          <Section
            title="Active model release"
            actions={
              <button type="button" className="secondary" onClick={() => onNavigate(releaseRoute)}>
                Open release
              </button>
            }
          >
            <DescriptionList
              items={[
                { term: "Name", value: release.name },
                { term: "Key", value: <code>{release.key}</code> },
                { term: "Version", value: release.version },
                { term: "Schema language", value: release.schemaVersion },
                { term: "Activated", value: formatServerTime(release.activatedAt) },
              ]}
            />
          </Section>
        </>
      )}
    </SettingsLayout>
  );
}
