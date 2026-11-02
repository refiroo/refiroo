/**
 * A job with neither items nor rows (a migration, a move, a batch and an import have them): one line
 * saying what it belongs to or produced, with a link to it where the caller can open the page (a
 * page for a group the caller does not hold is not offered, as the settings navigation does not list
 * it). A job with nothing to open says nothing more than its state; an assistant's mapping proposals
 * (`aiProposal`) show their tally.
 */

import { useHoldsGroup } from "@/app/useMe";
import { count } from "@/features/settings/limits";
import { routePath } from "@/routing/routes";
import type { Job, RouteState } from "@/types";
import { RouteLink } from "@/ui/RouteLink";
import { DescriptionList } from "@/ui/DescriptionList";
import { Section } from "@/ui/Section";

interface Produced {
  title: string;
  text: string;
  label: string;
  route: RouteState;
  /** The action groups any of which lets the caller open the page; none for a page everyone opens. */
  requires: string[];
}

const text = (value: unknown) => (typeof value === "string" && value ? value : undefined);

/** What a job leads to, from the parameters it was started with. */
export function producedBy(job: Job): Produced | undefined {
  const { parameters } = job;
  const taskId = text(parameters.taskId);
  if ((job.kind === "aiTask" || job.kind === "dryRun") && taskId)
    return {
      title: "The load",
      text: "This job belongs to a load of a workbook with the AI assistant.",
      label: "Open the load",
      route: { kind: "settings", page: "ai-tasks", taskId },
      requires: [],
    };
  const draftId = text(parameters.draftId);
  if ((job.kind === "inference" || job.kind === "dryRun") && draftId)
    return {
      title: "The model draft",
      text:
        job.kind === "inference"
          ? "This job read a file to propose changes to a model draft."
          : "This job checked a file against a model draft.",
      label: "Open the draft",
      route: { kind: "settings", page: "model", draftId },
      requires: ["model-authoring", "model-release"],
    };
  const mappingKey = text(parameters.mappingKey);
  const from = text(parameters.sourceWorkspaceKey);
  const to = text(parameters.targetWorkspaceKey);
  if (job.kind === "mappingInference" && mappingKey && from && to)
    return {
      title: "The mapping",
      text: `This job proposed what ${from} becomes in ${to}, in the mapping ${mappingKey}.`,
      label: "Open the mapping",
      route: { kind: "settings", page: "moves", move: { mappingKey, from, to } },
      requires: ["copy-move"],
    };
  const profileKey = text(parameters.profileKey);
  if (job.kind === "profileCheck" && profileKey)
    return {
      title: "The import profile",
      text: `This job checked a file against the import profile ${profileKey}.`,
      label: "Open the profile",
      route: { kind: "settings", page: "import-profiles", profileKey },
      requires: ["bulk"],
    };
  return undefined;
}

export function JobProduced({ job, onNavigate }: { job: Job; onNavigate?: (route: RouteState) => void }) {
  const produced = producedBy(job);
  const first = useHoldsGroup(produced?.requires[0] ?? "");
  const second = useHoldsGroup(produced?.requires[1] ?? "");
  const tally = job.aiProposal;
  const open = produced && (produced.requires.length === 0 || first || second);
  if (!open && !tally) return null;
  return (
    <>
      {produced && open && (
        <Section title={produced.title}>
          <p>
            {produced.text}{" "}
            <RouteLink href={routePath(produced.route)} onNavigate={() => onNavigate?.(produced.route)}>
              {produced.label}
            </RouteLink>
          </p>
        </Section>
      )}
      {tally && (
        <Section title="What it proposed">
          <DescriptionList
            className="compact"
            items={[
              { term: "Proposed", value: count(tally.proposed) },
              { term: "No match found", value: count(tally.unmatched) },
              { term: "Changed since it began", value: count(tally.changed) },
              { term: "Refused by the rules", value: count(tally.refused) },
              { term: "Not answered", value: count(tally.notAnswered) },
            ]}
          />
        </Section>
      )}
    </>
  );
}
