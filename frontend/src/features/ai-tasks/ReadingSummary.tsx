/** The first card of the reading (0.16 AP6a, board 5): what the file updates, what needs the person, what was skipped. */

import { useMemo } from "react";
import type { AiTask, ApplicationDefinition } from "@/types";
import { Card } from "@/ui/Card";
import { StatusPill } from "@/ui/StatusPill";
import { buildStructure } from "./aiTaskStructure";
import { languagesOf, needsPerson, plural, skippedByReading } from "./aiTaskText";

const listed = (names: string[]) =>
  names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : (names[0] ?? "");

export function ReadingSummary({ task, applications }: { task: AiTask; applications: ApplicationDefinition[] }) {
  const reading = task.reading;
  const updates = useMemo(() => (reading?.tables ?? []).filter((table) => table.as === "update"), [reading]);
  if (!reading) return null;
  const summary = reading.summary;
  const names = buildStructure(updates, applications).map((application) => application.name);
  const languages = [...new Set(updates.flatMap(languagesOf))];
  const need = summary?.needDecision ?? updates.filter(needsPerson).length;
  const lists = summary?.updates ?? updates.length;
  const types = summary?.types ?? new Set(updates.map((table) => table.objectTypeKey)).size;
  const sheets = summary?.sheets ?? new Set(reading.tables.map((table) => table.sheet)).size;
  const others = updates.filter((table) => !needsPerson(table)).length;
  const rows = updates.reduce((total, table) => total + table.rows, 0);
  const matched = updates.reduce((total, table) => total + table.matched, 0);
  const fresh = updates.reduce((total, table) => total + table.new, 0);
  const titles = skippedByReading(task).titles;
  return (
    <Card className="task-summary" aria-label="What the file does" as="section">
      {reading.profile && (
        <div>
          <StatusPill tone="success">{`Read as the profile “${reading.profile.name}”`}</StatusPill>
        </div>
      )}
      <p>
        <strong>{plural(lists, "list")}</strong> on {plural(sheets, "sheet")} {lists === 1 ? "updates" : "update"}{" "}
        <strong>{plural(types, "type")}</strong>
        {names.length > 0 && <> of {listed(names)}</>}
        {languages.length > 0 && <>, with their {listed(languages)} names as translations</>}.{" "}
        <strong>{need === 0 ? "Nothing needs you." : `${count(need)} ${need === 1 ? "needs" : "need"} you.`}</strong>
        {others > 0 && (
          <>
            {" "}
            {need === 0
              ? others === 1
                ? "It matches its stored records."
                : `All ${count(others)} match their stored records.`
              : others === 1
                ? "The other one matches its stored records."
                : `The other ${count(others)} match their stored records.`}
          </>
        )}
      </p>
      <ul>
        <li>
          {plural(rows, "row")}: {count(matched)} {matched === 1 ? "matches a stored record" : "match stored records"}
          {fresh > 0 && (
            <>
              , {plural(fresh, "key")} {fresh === 1 ? "is" : "are"} new
            </>
          )}
        </li>
        {titles > 0 && <li>Skipped as not data: {plural(titles, "title row")}</li>}
      </ul>
    </Card>
  );
}

const count = (n: number) => n.toLocaleString("en-GB");
