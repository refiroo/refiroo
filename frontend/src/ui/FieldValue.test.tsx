import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FieldValue } from "@/ui/FieldValue";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { ExpandedRelations, ObjectItem } from "@/types";

function expanded(direction: "outgoing" | "incoming", names: string[], count = names.length): ExpandedRelations {
  return {
    relationTypeKey: "domain-contains-codelist",
    direction,
    count,
    items: names.map((name, index) => ({
      relationId: `relation-${index}`,
      object: { id: `record-${index}`, objectTypeKey: "codelist", version: 1, fields: { name } },
    })),
    nextCursor: count > names.length ? "more" : null,
  };
}

function cell(item: ObjectItem, field: string) {
  return render(<FieldValue item={item} field={field} model={testModel} />).container;
}

describe("a relation column's cell (0.9 K5, D143)", () => {
  it.each([
    [[], 0, [], null],
    [["Alpha"], 1, ["Alpha"], null],
    [["Alpha", "Bravo", "Charlie"], 3, ["Alpha", "Bravo", "Charlie"], null],
    [["Alpha", "Bravo", "Charlie"], 5, ["Alpha", "Bravo", "Charlie"], "+2 more"],
  ])("shows %j of %i as chips with the rest counted", (names, count, shown, more) => {
    const item = { ...domainObject, expanded: [expanded("outgoing", names, count)] };
    const container = cell(item, "related:domain-contains-codelist");
    expect([...container.querySelectorAll(".record-chip-name")].map((chip) => chip.textContent)).toEqual(shown);
    expect(container.querySelector(".related-records-more")?.textContent ?? null).toBe(more);
    if (more)
      expect(container.querySelector(".related-records")).toHaveAttribute("title", "Alpha, Bravo, Charlie and 2 more");
  });

  it("reads the entry of the column's direction, empty when the row has none", () => {
    const item = { ...codelistObject, expanded: [expanded("incoming", ["Parent domain"])] };
    cell(item, "related:codelist-belongs-to-domain");
    expect(screen.getByText("Parent domain")).toBeInTheDocument();
    const other = cell(item, "related:domain-contains-codelist");
    expect(other.querySelector(".record-chip")).toBeNull();
  });
});

describe("a field column's cell (0.9 K5a, D149)", () => {
  it("shows each record's value of the field, a dash where it has none", () => {
    const entry = expanded("outgoing", ["Alpha", "Bravo", "Charlie"], 4);
    entry.field = "code";
    entry.items[0].object.fields.code = "AL";
    entry.items[1].object.fields.code = null;
    entry.items[2].object.fields.code = true;
    const container = cell({ ...domainObject, expanded: [entry] }, "related:domain-contains-codelist.code");
    expect([...container.querySelectorAll(".record-chip-name")].map((chip) => chip.textContent)).toEqual([
      "AL",
      "—",
      "Yes",
    ]);
    expect(container.querySelector(".related-records-more")?.textContent).toBe("+1 more");
    // The name column does not take the field's entry.
    expect(
      cell({ ...domainObject, expanded: [entry] }, "related:domain-contains-codelist").querySelector(".record-chip"),
    ).toBeNull();
  });
});
