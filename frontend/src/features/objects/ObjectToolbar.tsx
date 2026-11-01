import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ai } from "@/api/aiClient";
import { errorMessage } from "@/api/errors";
import { FilterBar, filterFields, filterPills, pillText } from "@/features/objects/filters/FilterBar";
import { relationshipFilterFields } from "@/model/lookup";
import { useRelationFilterNames } from "@/features/objects/RelationFilter";
import { useQueryTranslationOffer } from "@/features/settings/useWorkspaceAiOffer";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import type {
  CollectionFilter,
  CollectionQueryState,
  EngineModel,
  QueryTranslation,
  TableViewDefinition,
} from "@/types";
import { Choice } from "@/ui/Choice";
import { Notice } from "@/ui/Notice";
import { DebouncedSearchField, SearchField } from "@/ui/SearchField";

/** The stamps every record carries, filtered by on a live list without being declared (0.16 AG4). */
const STAMPS = ["createdAt", "updatedAt"];

/** Where a question in words stands: nothing asked, waiting, put on the list, held back, or failed. */
type Asked =
  | { kind: "idle" }
  | { kind: "asking" }
  | { kind: "applied"; signature: string }
  | { kind: "partial"; translation: QueryTranslation }
  | { kind: "failed"; message: string };

const signatureOf = (filters: readonly CollectionFilter[], search: string) => JSON.stringify([filters, search]);

export function ObjectToolbar({
  model,
  view,
  query,
  placeholder,
  onChange,
  display,
  sortMenu,
  workspaceKey,
  applicationKey,
  noun,
  countDraft,
}: {
  display: ReactNode;
  /** The sort menu, when a declared sort field has no visible column header. */
  sortMenu?: ReactNode;
  model: EngineModel;
  view: TableViewDefinition;
  query: CollectionQueryState;
  placeholder: string;
  onChange: (query: CollectionQueryState) => void;
  /** Where a relationship filter's record picker searches. */
  workspaceKey?: string;
  /** The application the list is shown in, which a question in words names with the view. */
  applicationKey?: string;
  /** The listed records' names, singular and plural, for the phone sheet's Show N. */
  noun: readonly [string, string];
  /** How many records the list shows with these filters, for the phone sheet (D163). */
  countDraft: (filters: CollectionFilter[]) => Promise<number | undefined>;
}) {
  const objectTypeKey = view.objectTypeKey ?? "";
  const { changeSet, publication } = useWorkspaceData();
  const live = !changeSet && !publication;
  const names = useRelationFilterNames(model, objectTypeKey, query.filters, workspaceKey);

  const offered = Boolean(useQueryTranslationOffer() && workspaceKey && applicationKey);
  const [mode, setMode] = useState<"search" | "ask">("search");
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState<Asked>({ kind: "idle" });
  const request = useRef<AbortController>(undefined);
  useEffect(() => () => request.current?.abort(), []);
  const asking = offered && mode === "ask";

  function ask(words: string) {
    const text = words.trim();
    if (!text || asked.kind === "asking" || !workspaceKey || !applicationKey) return;
    const controller = new AbortController();
    request.current = controller;
    setAsked({ kind: "asking" });
    ai.translateQuery(
      workspaceKey,
      {
        applicationKey,
        viewKey: view.key,
        question: text,
        ...(changeSet ? { changeSetId: changeSet.id } : {}),
        ...(publication ? { publicationId: publication.id } : {}),
      },
      controller.signal,
    )
      .then((answer) => {
        if (controller.signal.aborted) return;
        if (answer.applied) {
          onChange({ ...query, filters: answer.filters, search: answer.search });
          setAsked({ kind: "applied", signature: signatureOf(answer.filters, answer.search) });
        } else {
          setAsked({ kind: "partial", translation: answer });
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setAsked({ kind: "failed", message: errorMessage(error) });
      });
  }

  function cancel() {
    request.current?.abort();
    setAsked({ kind: "idle" });
  }

  function switchTo(next: "search" | "ask") {
    request.current?.abort();
    setAsked({ kind: "idle" });
    setMode(next);
  }

  const proposed = asked.kind === "partial" ? asked.translation : undefined;
  // A live list also filters by the two stamps; a change set or publication records none. A
  // relationship the view does not declare is drawn as a pill while a filter on it stands or is
  // proposed, as an answer in words may use any relationship of the type (0.16 AG4).
  const used = [...query.filters, ...(proposed?.filters ?? [])].map((filter) => filter.field).join("\n");
  const fields = useMemo(() => {
    const declared = view.config.filterFields;
    const stamps = live ? STAMPS.filter((stamp) => !declared.includes(stamp)) : [];
    const undeclared = relationshipFilterFields(model, objectTypeKey).filter(
      (field) => !declared.includes(field) && used.split("\n").includes(field),
    );
    return filterFields(model, [...declared, ...stamps, ...undeclared]);
  }, [model, objectTypeKey, view.config.filterFields, live, used]);
  const proposedNames = useRelationFilterNames(model, objectTypeKey, proposed?.filters ?? [], workspaceKey);
  const applied =
    asked.kind === "applied" && asked.signature === signatureOf(query.filters, query.search) ? asked : undefined;

  return (
    <>
      <div className="collection-toolbar object-toolbar">
        {offered && (
          <div role="group" aria-label="Search or ask" className="ask-switch">
            <Choice
              name={`${view.key}-search-mode`}
              value={mode}
              options={[
                ["search", "Search"],
                ["ask", "Ask"],
              ]}
              onChange={switchTo}
            />
          </div>
        )}
        {asking ? (
          <SearchField
            value={question}
            onChange={setQuestion}
            onSubmit={ask}
            label="Ask in words"
            placeholder={`Ask about ${noun[1].toLowerCase()}, then press Enter`}
          />
        ) : (
          <DebouncedSearchField
            key={query.search}
            appliedValue={query.search}
            placeholder={placeholder}
            onApply={(search) => onChange({ ...query, search })}
          />
        )}
        <FilterBar
          model={model}
          objectTypeKey={objectTypeKey}
          fields={fields}
          filters={query.filters}
          names={names}
          workspaceKey={workspaceKey}
          noun={noun}
          countDraft={countDraft}
          onChange={(filters) => onChange({ ...query, filters })}
        />
        <div className="object-toolbar-end">
          {display}
          {sortMenu}
        </div>
      </div>
      {query.search !== "" && query.filters.length > 0 && (
        <div className="filter-chips" aria-label="Applied search">
          <button className="ghost" onClick={() => onChange({ ...query, search: "", filters: [] })}>
            Clear search and filters
          </button>
        </div>
      )}
      {asked.kind === "asking" && (
        <div className="ask-status">
          <Notice
            actions={
              <button type="button" className="secondary" onClick={cancel}>
                Cancel
              </button>
            }
          >
            Asking…
          </Notice>
        </div>
      )}
      {asked.kind === "failed" && (
        <div className="ask-status">
          <Notice tone="error">{asked.message}</Notice>
        </div>
      )}
      {applied && <p className="ask-note">Your question became these filters. Change or remove any of them.</p>}
      {proposed && (
        <div className="ask-status">
          <Notice tone="warning" title="This list cannot answer all of that, so nothing was applied.">
            {proposed.notExpressed.map((item) => (
              <p key={item.part}>
                Not possible here: <b>{item.part}</b>. {item.reason}
              </p>
            ))}
            {(proposed.filters.length > 0 || proposed.search !== "") && (
              <>
                <div className="ask-proposed">
                  <span className="ask-proposed-label">What it could do:</span>
                  {filterPills(fields, proposed.filters).map(({ spec, entries }, index) => {
                    const text = pillText(spec, entries, proposedNames);
                    return (
                      <span key={`${spec.field}:${index}`} className="filter-pill proposed">
                        <span className="filter-pill-label">{text.label}</span>{" "}
                        <span className="filter-pill-value">{text.value}</span>
                      </span>
                    );
                  })}
                  {proposed.search !== "" && (
                    <span className="filter-pill proposed">
                      <span className="filter-pill-label">Search</span>{" "}
                      <span className="filter-pill-value">{proposed.search}</span>
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    onChange({ ...query, filters: proposed.filters, search: proposed.search });
                    setAsked({ kind: "applied", signature: signatureOf(proposed.filters, proposed.search) });
                  }}
                >
                  Use these filters
                </button>
              </>
            )}
          </Notice>
        </div>
      )}
    </>
  );
}
