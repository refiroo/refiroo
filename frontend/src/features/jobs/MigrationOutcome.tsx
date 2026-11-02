/**
 * What a migration job did (its page, `/settings/jobs/{id}`): one sentence and the four counts of
 * its summary, then its items by outcome, converted, type changed, removed or must be fixed. The
 * items are the migration page's own table (`features/model-admin/MigrationRows`); the migration
 * page itself, where a preview is reviewed and confirmed, stays in Settings › Model.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { count } from "@/features/settings/limits";
import { MIGRATION_OUTCOMES, MigrationRows } from "@/features/model-admin/MigrationRows";
import type { EngineModel, Job, MigrationOutcome as Outcome, MigrationSummary } from "@/types";
import { Choice } from "@/ui/Choice";
import { OutcomeCards } from "@/ui/OutcomeCards";
import { Section } from "@/ui/Section";

export function MigrationOutcome({ job, summary, model }: { job: Job; summary: MigrationSummary; model: EngineModel }) {
  const [models, setModels] = useState<{ current: EngineModel; target: EngineModel }>();
  const { counts } = summary;
  const [show, setShow] = useState<Outcome>(
    counts.refused ? "refused" : (MIGRATION_OUTCOMES.find((item) => counts[item.key] > 0)?.key ?? "conversion"),
  );
  useEffect(() => {
    let active = true;
    Promise.all([api.modelRelease(summary.currentReleaseId, true), api.modelRelease(summary.targetReleaseId, true)])
      .then(([current, target]) => {
        if (active && current.model && target.model)
          setModels({
            current: current.model as unknown as EngineModel,
            target: target.model as unknown as EngineModel,
          });
      })
      // Without the two releases' models the rows name types and fields by their keys.
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [summary.currentReleaseId, summary.targetReleaseId]);
  const shown = models ?? { current: model, target: model };
  const version = models?.target.release.version ?? "the release";
  const moving = job.parameters.moves === "changeSet";
  const loaded = Boolean(job.confirmedAt);
  const [past, ing] = moving ? ["Moved", "moving"] : ["Migrated", "migrating"];
  const sentence = `${loaded ? past : `Preview of ${ing}`} ${job.workspaceKey} to ${
    models ? `release ${version}` : "the release"
  }: ${count(counts.conversion)} values converted, ${count(counts.reclassified)} records changed type, ${count(counts.loss)} items removed, ${count(counts.refused)} must be fixed.`;
  return (
    <>
      <Section title="What happened">
        <p className="job-sentence">{sentence}</p>
        <OutcomeCards
          label="What the migration did"
          items={MIGRATION_OUTCOMES.map((item) => ({
            key: item.key,
            count: counts[item.key],
            label: item.label,
            tone: item.key === "refused" ? "error" : item.key === "loss" ? "warning" : undefined,
          }))}
        />
      </Section>
      <Section title="The items">
        <div className="job-filters">
          <Choice
            name={`migration-items-${job.id}`}
            value={show}
            options={MIGRATION_OUTCOMES.map(
              (item) => [item.key, `${item.label} (${count(counts[item.key])})`] as const,
            )}
            onChange={setShow}
          />
        </div>
        <MigrationRows
          key={`${job.id}:${show}`}
          jobId={job.id}
          outcome={show}
          empty={MIGRATION_OUTCOMES.find((item) => item.key === show)!.empty}
          models={shown}
          version={version}
          moving={moving}
        />
      </Section>
    </>
  );
}
