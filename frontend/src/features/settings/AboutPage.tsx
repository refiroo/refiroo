/**
 * Settings › About (Track U U3): what this deployment runs, from `GET /system` (J31): the engine
 * and management API version, the schema languages and the active model release. The database's
 * migration revision is the operator's, on Deployment (0.12 D246).
 */

import { API_URL } from "@/api/address";
import { formatServerTime } from "@/lib/dates";
import type { SettingsRoute } from "@/types";
import { DescriptionList } from "@/ui/DescriptionList";
import { InlineError } from "@/ui/InlineError";
import { ProductMark } from "@/ui/ProductMark";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { Skeleton } from "@/ui/Skeleton";
import { useSystem } from "./useSystem";

export function AboutPage({ onNavigate }: { onNavigate: (route: SettingsRoute) => void }) {
  const { system, error, retry } = useSystem();
  const release = system?.activeModelRelease;
  const build = system?.engine.build ?? { commit: null, tag: null };
  // The source address may name the tree of the version (the default); a build's links start at the repository.
  const repository = (system?.engine.sourceCode ?? "").replace(/\/tree\/.*$/, "").replace(/\/$/, "");
  const releaseRoute: SettingsRoute | undefined = release && { kind: "settings", page: "model", releaseId: release.id };
  return (
    <SettingsLayout eyebrow="General" title="About" description="What this deployment runs.">
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !system || !release || !releaseRoute ? (
        <Skeleton label="Loading what this deployment runs" lines={6} />
      ) : (
        <>
          <Section title="refiroo">
            <div className="about-brand">
              <ProductMark name="refiroo" />
              <p className="about-tagline">Reference data that stays in step.</p>
              <p>
                refiroo is where your organisation keeps the lists everything else depends on: codes, categories,
                translations and the way one system&rsquo;s value maps to another&rsquo;s. You describe a domain once in
                a model and refiroo gives it screens, an API, validation, history and search. Corrections go live when
                saved, bigger changes are prepared in a change set and published together, and every record remembers
                who changed it and when.
              </p>
              <ul className="about-points">
                <li>
                  <strong>Shape it to your domain.</strong> Another domain is another model, not another product.
                </li>
                <li>
                  <strong>Connect, don&rsquo;t copy.</strong> Hierarchies, relationships and mappings keep their
                  meaning.
                </li>
                <li>
                  <strong>One API for everything.</strong> What the browser does, your integrations can do.
                </li>
              </ul>
              <p className="about-links">
                Read more: the <a href={`${API_URL}/docs/`}>documentation</a>, the{" "}
                <a href={`${API_URL}/docs/api`}>API reference</a>, and in the repository <code>README.md</code>,{" "}
                <code>docs/PRODUCT.md</code> (what it does), <code>docs/MODEL_AUTHORING.md</code> (writing a model) and{" "}
                <code>docs/API.md</code> (the contracts). Under the hood refiroo runs on the RDM engine, shown below.
              </p>
            </div>
          </Section>
          <Section title="Engine">
            <DescriptionList
              items={[
                { term: "Engine version", value: system.engine.version },
                { term: "Management API", value: <code>{system.engine.managementApi}</code> },
                { term: "Schema languages", value: system.schemaLanguages.join(", ") },
                { term: "Licence", value: system.engine.license },
                ...(build.tag || build.commit
                  ? [
                      {
                        term: "Build",
                        value: (
                          <>
                            {build.tag && (
                              <a href={`${repository}/releases/tag/${build.tag}`} target="_blank" rel="noreferrer">
                                {build.tag}
                              </a>
                            )}
                            {build.tag && build.commit && " "}
                            {build.commit && (
                              <a
                                href={`${repository}/commit/${build.commit}`}
                                target="_blank"
                                rel="noreferrer"
                                className="mono"
                              >
                                {build.commit}
                              </a>
                            )}
                          </>
                        ),
                      },
                    ]
                  : []),
                {
                  term: "Source code",
                  value: (
                    <a href={system.engine.sourceCode} target="_blank" rel="noreferrer">
                      {system.engine.sourceCode}
                    </a>
                  ),
                },
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
