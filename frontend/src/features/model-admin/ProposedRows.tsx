/**
 * What a model draft proposes for a migration (0.13 MG, the approved mock-up): the page opens filled in from
 * `GET /model-drafts/{id}/migration`, each row marked Proposed and changeable in place, never as an
 * accept-or-reject list. A change here is a new preview; it does not change the draft. The rows are the
 * types the draft's steps change (what they become, where their records go, under what); a split, a list
 * conversion and a relation type's new key follow as lines.
 */

import { ProposedPill } from "@/features/model-editor/ProposedBecause";
import type { DraftMigration, DraftMigrationRow, EngineModel } from "@/types";

const NOT_KEPT = "";

const count = (value: number | string) => (typeof value === "number" ? value.toLocaleString("en-GB") : value);

const PARENT_WORDS: Record<DraftMigrationRow["parent"], string> = {
  unchanged: "Unchanged",
  topLevel: "Top level",
  changed: "Under other types",
};

export function ProposedRows({
  proposal,
  target,
  choices,
  disabled,
  onChoose,
}: {
  proposal: DraftMigration;
  /** The release the migration goes to, whose types a row may become. */
  target: EngineModel;
  /** The page's choices (`type:{from}` to the type it became, empty for not kept). */
  choices: Record<string, string>;
  disabled: boolean;
  onChoose: (typeKey: string, becomes: string) => void;
}) {
  const applicationName = (key: string) => target.applications.find((item) => item.key === key)?.name ?? key;
  const typeName = (key: string) => target.objectTypes.find((item) => item.key === key)?.name ?? key;
  const attributeName = (key: string) => target.attributeTypes.find((item) => item.key === key)?.name ?? key;
  const lines = [
    ...proposal.splits.map(
      (item) =>
        `Split: ${typeName(item.fromObjectTypeKey)} gets a ${typeName(item.toObjectTypeKey)} record for each value of ${item.attributes.map(attributeName).join(", ")}`,
    ),
    ...proposal.listConversions.map(
      (item) =>
        `List: the values of ${attributeName(item.attributeTypeKey)} become ${typeName(item.toObjectTypeKey)} records`,
    ),
    ...proposal.relationTypeMappings.map(
      (item) => `Relationships ${item.fromRelationTypeKey} → ${item.toRelationTypeKey}`,
    ),
  ];
  return (
    <section aria-labelledby="migration-proposed" className="migration-section">
      <h2 id="migration-proposed" className="install-heading">
        What the draft proposes
      </h2>
      <p className="muted">
        These come from the steps of the draft. Change a row here and the migration previews again; the draft stays as
        it is.
      </p>
      {proposal.rows.length > 0 && (
        <div className="migration-proposed-wrap">
          <table className="migration-proposed">
            <thead>
              <tr>
                <th scope="col">Records of</th>
                <th scope="col">Become</th>
                <th scope="col">In</th>
                <th scope="col">Under</th>
                <th scope="col" className="num">
                  Records
                </th>
                <th scope="col">
                  <span className="visually-hidden">Status</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {proposal.rows.map((row) => {
                const chosen = choices[`type:${row.fromObjectTypeKey}`] ?? row.fromObjectTypeKey;
                const proposed = chosen === row.toObjectTypeKey;
                const where = row.toApplicationKey
                  ? applicationName(row.toApplicationKey)
                  : row.toApplicationKeys.map(applicationName).join(", ");
                return (
                  <tr key={row.fromObjectTypeKey}>
                    <td>
                      {row.fromName}
                      <br />
                      <small className="muted">{row.fromApplicationKeys.map(applicationName).join(", ")}</small>
                    </td>
                    <td>
                      <select
                        aria-label={`${row.fromName} becomes`}
                        value={chosen}
                        disabled={disabled}
                        onChange={(event) => onChoose(row.fromObjectTypeKey, event.target.value)}
                      >
                        {target.objectTypes.map((type) => (
                          <option key={type.key} value={type.key}>
                            {type.name}
                          </option>
                        ))}
                        <option value={NOT_KEPT}>Not kept</option>
                      </select>
                    </td>
                    <td>{where}</td>
                    <td>{PARENT_WORDS[row.parent]}</td>
                    <td className="num">{count(row.records.records)}</td>
                    <td>{proposed && <ProposedPill />}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {lines.length > 0 && (
        <ul className="migration-proposed-lines">
          {lines.map((line) => (
            <li key={line}>
              {line} <ProposedPill />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
