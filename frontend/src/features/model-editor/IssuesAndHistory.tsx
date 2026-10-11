/**
 * The editor's issues and history (0.10 A4a). Issues are the compiler's diagnostics of the draft,
 * each linked to the element the server tied it to (D36). History lists the draft's steps newest
 * first, in plain words, with their time and whether they were undone; a step not undone can be
 * undone from its line, and one that later steps depend on is offered to undo with them (D8).
 */

import type { EditorSelection, ModelDraftOutline, OutlineDiagnostic, OutlineElement } from "@/types";
import { formatServerTime } from "@/lib/dates";
import type { CursorFeed } from "@/lib/hooks/useCursorFeed";
import type { ModelDraftOperationEntry } from "@/types";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { describeStep, historySteps, undoable } from "@/features/model-editor/history";
import { elementLabel, nameOf } from "@/features/model-editor/outline";

/** Where an issue's link goes: the element's own panel, the matrix for a relation between two types. */
export function selectionFor(element: OutlineElement): EditorSelection {
  if (element.objectType) return { show: "type", key: element.objectType };
  if (element.relationType && element.from) return { show: "matrix" };
  if (element.relationType) return { show: "relationType", key: element.relationType };
  if (element.attributeType) return { show: "attributeType", key: element.attributeType };
  if (element.applicationKey) return { show: "application", key: element.applicationKey };
  return {};
}

export function IssuesAndHistory({
  outline,
  tab,
  onTab,
  history,
  onSelect,
  onUndoStep,
}: {
  outline: ModelDraftOutline;
  tab: string;
  onTab: (tab: string) => void;
  history: CursorFeed<ModelDraftOperationEntry>;
  onSelect: (selection: EditorSelection) => void;
  onUndoStep: (step: number) => void;
}) {
  const names = nameOf(outline);
  const steps = historySteps(history.items);
  const issues = outline.diagnostics;
  return (
    <Tabs
      label="Draft"
      selected={tab}
      onChange={onTab}
      tabs={[
        {
          id: "issues",
          label: `Issues (${issues.length})`,
          content: issues.length ? (
            <ul className="editor-issues">
              {issues.map((issue, index) => (
                <Issue key={`${issue.path}:${index}`} issue={issue} outline={outline} onSelect={onSelect} />
              ))}
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
                      <span className="editor-history-text">{describeStep(step, names)}</span>
                      <span className="editor-history-at">{formatServerTime(step.at)}</span>
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
      ]}
    />
  );
}

function Issue({
  issue,
  outline,
  onSelect,
}: {
  issue: OutlineDiagnostic;
  outline: ModelDraftOutline;
  onSelect: (selection: EditorSelection) => void;
}) {
  const target = issue.element ? selectionFor(issue.element) : {};
  return (
    <li>
      <StatusPill tone={issue.severity === "error" ? "error" : "warning"}>
        {issue.severity === "error" ? "Error" : "Warning"}
      </StatusPill>
      <span className="editor-issue-text">{issue.message}</span>
      {issue.element && target.show ? (
        <button type="button" className="link-button" onClick={() => onSelect(target)}>
          Go to {elementLabel(outline, issue.element)}
        </button>
      ) : (
        <code className="element-key">{issue.path}</code>
      )}
    </li>
  );
}
