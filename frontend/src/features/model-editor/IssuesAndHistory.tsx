/**
 * The editor's issues and history (0.10 A4a). Issues are the compiler's diagnostics of the draft,
 * each linked to the element the server tied it to (D36). History lists the draft's steps newest
 * first, in plain words, with their time and whether they were undone; a step not undone can be
 * undone from its line, and one that later steps depend on is offered to undo with them (D8).
 *
 * With a source file (0.10 A5b), Issues lists the draft profile's warnings too, each linked to its
 * column, and a third tab holds the dry run.
 */

import type { ReactNode } from "react";
import type { DraftProfile, EditorSelection, ModelDraftOutline, OutlineDiagnostic, OutlineElement } from "@/types";
import { formatServerTime } from "@/lib/dates";
import type { CursorFeed } from "@/lib/hooks/useCursorFeed";
import type { ModelDraftOperationEntry } from "@/types";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { describeStep, historySteps, migrationWords, undoable } from "@/features/model-editor/history";
import { elementLabel, nameOf } from "@/model/outline";
import { columnsOfIssue } from "@/features/model-editor/mapping";
import { ActorName } from "@/ui/ActorName";
import { PROFILE_KEY_MISMATCH, PROFILE_KEY_POINTER, UseFreeKey } from "@/features/model-editor/ProfileKeyConflict";

/**
 * Where an issue's link goes: the element's own panel, the matrix for a relation between two types,
 * a detail page or one of its panels to the page's type.
 */
export function selectionFor(element: OutlineElement): EditorSelection {
  if (element.consumerApi) return { show: "consumerApi", key: element.consumerApi };
  if (element.objectType) return { show: "type", key: element.objectType };
  if (element.applicationKey && element.detail)
    return { show: "type", key: element.detail, application: element.applicationKey };
  if (element.relationType && element.from) return { show: "matrix" };
  if (element.relationType) return { show: "relationType", key: element.relationType };
  if (element.attributeType) return { show: "attributeType", key: element.attributeType };
  if (element.applicationKey && element.group)
    return { show: "group", application: element.applicationKey, key: element.group };
  if (element.applicationKey) return { show: "application", key: element.applicationKey };
  return {};
}

/** An issue's link: where the editor goes, and the element the server tied the issue to (a page may go nearer). */
export type IssueTarget = (selection: EditorSelection, element?: OutlineElement) => void;

export function IssuesAndHistory({
  outline,
  tab,
  onTab,
  history,
  onSelect,
  onUndoStep,
  profile,
  dryRun,
  onUseProfileKey,
  onGoToProfileKey,
  onRemovePanel,
}: {
  outline: ModelDraftOutline;
  tab: string;
  onTab: (tab: string) => void;
  history: CursorFeed<ModelDraftOperationEntry>;
  onSelect: IssueTarget;
  onUndoStep: (step: number) => void;
  /** The draft's profile, whose warnings join the issues. */
  profile?: DraftProfile;
  /** The dry run tab's content, with a source file. */
  dryRun?: { label: string; content: ReactNode };
  /** Sets the profile's key (a conflict offers the free one); without it no action is offered. */
  onUseProfileKey?: (key: string) => void;
  /** Moves to the profile key's field in the source pane. */
  onGoToProfileKey?: () => void;
  /** Takes a panel off its page; without it the issue offers no such action. */
  onRemovePanel?: (page: { applicationKey: string; detail: string; panel: string }) => void;
}) {
  const names = nameOf(outline);
  const steps = historySteps(history.items);
  const issues = outline.diagnostics;
  const profileIssues = profile?.profile ? profile.diagnostics : [];
  const count = issues.length + profileIssues.length;
  return (
    <Tabs
      label="Draft"
      selected={tab}
      onChange={onTab}
      tabs={[
        {
          id: "issues",
          label: `Issues (${count})`,
          content: count ? (
            <ul className="editor-issues">
              {issues.map((issue, index) => (
                <Issue
                  key={`${issue.path}:${index}`}
                  issue={issue}
                  outline={outline}
                  onSelect={onSelect}
                  onRemovePanel={onRemovePanel}
                />
              ))}
              {profileIssues.map((issue, index) => {
                const [column] = profile?.profile ? columnsOfIssue(profile.profile, issue) : [];
                return (
                  <li key={`${issue.path}:${index}`}>
                    <StatusPill tone={issue.severity === "error" ? "error" : "warning"}>
                      {issue.severity === "error" ? "Error" : "Warning"}
                    </StatusPill>
                    <span className="editor-issue-text">{issue.message}</span>
                    {issue.code === PROFILE_KEY_MISMATCH && profile?.freeKey && onUseProfileKey ? (
                      <UseFreeKey freeKey={profile.freeKey} onUse={() => onUseProfileKey(profile.freeKey as string)} />
                    ) : null}
                    {issue.path === PROFILE_KEY_POINTER && onGoToProfileKey ? (
                      <button type="button" className="link-button" onClick={onGoToProfileKey}>
                        Go to the profile key
                      </button>
                    ) : column ? (
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => onSelect({ show: "column", sheet: column.sheet, key: column.header })}
                      >
                        Go to column {column.header}
                      </button>
                    ) : (
                      <code className="element-key">{issue.path}</code>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState>No issues: the draft is valid and can be installed.</EmptyState>
          ),
        },
        {
          id: "history",
          label: "History",
          content: (
            <div className="editor-history">
              {history.error && <InlineError message={history.error} onRetry={history.retry} />}
              {!history.error && !history.loading && !steps.length && <EmptyState>No steps yet.</EmptyState>}
              {steps.length > 0 && (
                <ol className="editor-history-list" aria-label="Steps, newest first">
                  {steps.map((step) => (
                    <li key={step.step} className={step.undone ? "undone" : undefined}>
                      <span className="editor-history-step">#{step.step}</span>
                      <span className="editor-history-text">
                        {describeStep(step, names)}
                        {migrationWords(step, names) && (
                          <span className="editor-history-migration">
                            <StatusPill tone="warning">Needs a migration</StatusPill>
                            {migrationWords(step, names)}
                          </span>
                        )}
                      </span>
                      <span className="editor-history-at">
                        {formatServerTime(step.at)} <ActorName actor={step.entries[0]?.author ?? null} />
                        {step.origin.proposedByName && `, asked for by ${step.origin.proposedByName}`}
                      </span>
                      <span className="editor-history-state">
                        {step.undone ? "Undone" : step.origin.type === "patch" ? "JSON edit" : "Applied"}
                      </span>
                      {undoable(step) ? (
                        <button
                          type="button"
                          className="link-button"
                          aria-label={`Undo step ${step.step}`}
                          onClick={() => onUndoStep(step.step)}
                        >
                          Undo
                        </button>
                      ) : (
                        <span />
                      )}
                    </li>
                  ))}
                </ol>
              )}
              {history.hasMore && (
                <button type="button" className="load-more" disabled={history.loading} onClick={history.loadMore}>
                  Earlier steps
                </button>
              )}
            </div>
          ),
        },
        ...(dryRun ? [{ id: "dryRun", label: dryRun.label, content: dryRun.content }] : []),
      ]}
    />
  );
}

function Issue({
  issue,
  outline,
  onSelect,
  onRemovePanel,
}: {
  issue: OutlineDiagnostic;
  outline: ModelDraftOutline;
  onSelect: IssueTarget;
  onRemovePanel?: (page: { applicationKey: string; detail: string; panel: string }) => void;
}) {
  const target = issue.element ? selectionFor(issue.element) : {};
  const { applicationKey, detail, panel } = issue.element ?? {};
  return (
    <li>
      <StatusPill tone={issue.severity === "error" ? "error" : "warning"}>
        {issue.severity === "error" ? "Error" : "Warning"}
      </StatusPill>
      <span className="editor-issue-text">{issue.message}</span>
      {issue.element && target.show ? (
        <button type="button" className="link-button" onClick={() => onSelect(target, issue.element ?? undefined)}>
          Go to {elementLabel(outline, issue.element)}
        </button>
      ) : (
        <code className="element-key">{issue.path}</code>
      )}
      {onRemovePanel && applicationKey && detail && panel ? (
        <button type="button" className="link-button" onClick={() => onRemovePanel({ applicationKey, detail, panel })}>
          Remove from page
        </button>
      ) : null}
    </li>
  );
}
