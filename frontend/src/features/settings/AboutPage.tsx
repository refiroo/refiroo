/**
 * Settings › About (Track U U3): what this deployment runs, from `GET /system` (J31): the engine
 * and management API version, the schema languages and the active model release. The database's
 * migration revision is the operator's, on Deployment (0.12 D246).
 */

import { API_URL } from "@/api/address";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import type { SettingsRoute } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { ProductMark } from "@/ui/ProductMark";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingRow, SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { settingsHead } from "@/ui/settingsNavigation";
import { useSystem } from "@/state/useSystem";

export function AboutPage({ onNavigate }: { onNavigate: (route: SettingsRoute) => void }) {
  const { system, error, retry } = useSystem();
  const release = system?.activeModelRelease;
  const build = system?.engine.build ?? { commit: null, tag: null };
  // The source address may name the tree of the version (the default); a build's links start at the repository.
  const repository = (system?.engine.sourceCode ?? "").replace(/\/tree\/.*$/, "").replace(/\/$/, "");
  const releaseRoute: SettingsRoute | undefined = release && { kind: "settings", page: "model", releaseId: release.id };
  return (
    <SettingsLayout {...settingsHead("about")} title="About" description="What this deployment runs.">
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !system || !release || !releaseRoute ? (
        <Skeleton label="Loading what this deployment runs" lines={6} />
      ) : (
        <>
          <SettingsGroup title="refiroo" description="What it is for.">
            <SettingsPanel className="settings-panel-pad">
              <div className="about-brand">
                <ProductMark name="refiroo" />
                <p className="about-tagline">Reference data that stays in step.</p>
                <p>
                  refiroo is where your organisation keeps the lists everything else depends on: codes, categories,
                  translations and the way one system&rsquo;s value maps to another&rsquo;s. You describe a domain once
                  in a model and refiroo gives it screens, an API, validation, history and search. Corrections go live
                  when saved, bigger changes are prepared in a change set and published together, and every record
                  remembers who changed it and when.
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
                  <code>docs/PRODUCT.md</code> (what it does), <code>docs/MODEL_AUTHORING.md</code> (writing a model)
                  and <code>docs/API.md</code> (the contracts). Under the hood refiroo runs on the RDM engine, shown
                  below.
                </p>
              </div>
            </SettingsPanel>
          </SettingsGroup>
          <SettingsGroup title="Engine" description="The version this instance runs and where its source is.">
            <SettingsPanel>
              <SettingRow fact name="Engine version">
                {system.engine.version}
              </SettingRow>
              <SettingRow fact name="Management API">
                <code>{system.engine.managementApi}</code>
              </SettingRow>
              <SettingRow fact name="Schema languages">
                {system.schemaLanguages.join(", ")}
              </SettingRow>
              <SettingRow fact name="Licence">
                {system.engine.license}
              </SettingRow>
              {(build.tag || build.commit) && (
                <SettingRow fact name="Build">
                  <span>
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
                  </span>
                </SettingRow>
              )}
              <SettingRow fact name="Source code">
                <a href={system.engine.sourceCode} target="_blank" rel="noreferrer">
                  {system.engine.sourceCode}
                </a>
              </SettingRow>
            </SettingsPanel>
          </SettingsGroup>
          <SettingsGroup
            title="Active model release"
            description="The model release the engine serves now."
            action={
              <button type="button" className="secondary" onClick={() => onNavigate(releaseRoute)}>
                Open release
              </button>
            }
          >
            <SettingsPanel>
              <SettingRow fact name="Name">
                {release.name}
              </SettingRow>
              <SettingRow fact name="Key">
                <code>{release.key}</code>
              </SettingRow>
              <SettingRow fact name="Version">
                {release.version}
              </SettingRow>
              <SettingRow fact name="Schema language">
                {release.schemaVersion}
              </SettingRow>
              <SettingRow fact name="Activated">
                <span title={formatServerTime(release.activatedAt)}>{formatServerDayTime(release.activatedAt)}</span>
              </SettingRow>
            </SettingsPanel>
          </SettingsGroup>
        </>
      )}
    </SettingsLayout>
  );
}
