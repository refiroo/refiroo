import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { criteriaFromFilters } from "@/features/jobs/exportRequest";
import { FilterBar, filterFields, filterPills, pillText } from "@/features/objects/filters/FilterBar";
import { relationFilterEntries, relationFilterMode, relationFilterText } from "@/features/objects/RelationFilter";
import { relatedAncestorTypes } from "@/model/lookup";
import { domainObject, testModel } from "@/test/fixtures";
import type { CollectionFilter } from "@/types";

afterEach(() => vi.restoreAllMocks());

// The domain list's relationship to the codelists it contains: a codelist stands under a domain.
const relation = "related:domain-contains-codelist";
const fields = filterFields(testModel, ["code", "updatedAt", relation]);
const names = new Map([["d1", { id: "d1", name: "Delivery Methods", objectTypeKey: "domain" }]]);

function bar(filters: CollectionFilter[], onChange = vi.fn()) {
  render(
    <FilterBar
      model={testModel}
      objectTypeKey="domain"
      fields={fields}
      filters={filters}
      names={names}
      noun={["Domain", "Domains"]}
      countDraft={async () => 1}
      onChange={onChange}
    />,
  );
  return onChange;
}

describe("has none under, has any under (0.16 AG4)", () => {
  it("reads the types the related records can stand under from the served placements", () => {
    expect(relatedAncestorTypes(testModel, "domain", relation).map((type) => type.key)).toEqual(["domain"]);
    expect(relatedAncestorTypes(testModel, "codelist", "related:codelist-belongs-to-domain")).toEqual([]);
  });

  it("stores one entry naming the record and words it as a pill", () => {
    const none = relationFilterEntries(relation, "notUnder", [{ id: "d1", name: "Delivery Methods" }]);
    expect(none).toEqual([{ field: relation, operator: "notUnder", value: "d1" }]);
    expect(relationFilterEntries(relation, "under", [])).toEqual([]);
    expect(relationFilterMode(none)).toBe("notUnder");
    expect(relationFilterText(none, names)).toBe("has none under Delivery Methods");
    const spec = fields.find((item) => item.field === relation)!;
    expect(pillText(spec, none, names).value).toBe("has none under Delivery Methods");
    expect(pillText(spec, [{ field: relation, operator: "under", value: "d1" }], names).value).toBe(
      "has any under Delivery Methods",
    );
  });

  it("offers the two modes, applies only once a record is chosen, and keeps one record", async () => {
    vi.spyOn(api, "objects").mockResolvedValue({
      items: [
        { ...domainObject, id: "d1", name: "Delivery Methods" },
        { ...domainObject, id: "d2", name: "Payment Methods" },
      ],
      nextCursor: null,
    });
    const onChange = bar([]);
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const menu = await screen.findByRole("dialog", { name: "Filter" });
    fireEvent.click(within(menu).getByRole("button", { name: /^Contains/ }));
    const editor = await screen.findByLabelText("Filter by Contains");
    fireEvent.click(within(editor).getByRole("radio", { name: "Has none under" }));
    expect(within(editor).getByRole("button", { name: "Apply" })).toBeDisabled();
    const list = await within(editor).findByRole("group", { name: "Domains" });
    fireEvent.click(within((await within(list).findByText("Payment Methods")).closest("label")!).getByRole("checkbox"));
    fireEvent.click(
      within((await within(list).findByText("Delivery Methods")).closest("label")!).getByRole("checkbox"),
    );
    expect(within(editor).getByText("1 selected")).toBeInTheDocument();
    fireEvent.click(within(editor).getByRole("button", { name: "Apply" }));
    expect(onChange).toHaveBeenLastCalledWith([{ field: relation, operator: "notUnder", value: "d1" }]);
  });

  it("shows the pill and reopens in the mode it was applied in", async () => {
    bar([{ field: relation, operator: "notUnder", value: "d1" }]);
    const pill = screen.getByRole("button", { name: /^Contains: has none under Delivery Methods/ });
    fireEvent.click(pill);
    const editor = await screen.findByLabelText("Filter by Contains");
    expect(within(editor).getByRole("radio", { name: "Has none under" })).toBeChecked();
  });

  it("becomes the query's related hop with the ancestor criterion of the record's own type", () => {
    const filters = relationFilterEntries(relation, "notUnder", [{ id: "d1", name: "Delivery Methods" }]);
    const records = new Map([["d1", { objectTypeKey: "domain" }]]);
    expect(criteriaFromFilters(testModel, filters, records)).toEqual([
      {
        related: {
          relationTypeKey: "domain-contains-codelist",
          direction: "outgoing",
          where: [{ field: "ancestor:domain", op: "eq", value: "d1" }],
        },
        not: true,
      },
    ]);
    expect(criteriaFromFilters(testModel, filters)).toEqual([]);
  });
});

describe("two conditions on one field (0.16 AG4)", () => {
  const range: CollectionFilter[] = [
    { field: "updatedAt", operator: "gte", value: "2026-10-01" },
    { field: "updatedAt", operator: "lt", value: "2026-11-01" },
  ];

  it("are a pill each, and removing one keeps the other", () => {
    expect(filterPills(fields, range).map(({ entries }) => entries.length)).toEqual([1, 1]);
    const onChange = bar(range);
    const pills = within(screen.getByRole("group", { name: "Filters" }));
    expect(pills.getByRole("button", { name: /^Updated on or after: 2026-10-01/ })).toBeInTheDocument();
    expect(pills.getByRole("button", { name: /^Updated before: 2026-11-01/ })).toBeInTheDocument();
    fireEvent.click(pills.getAllByRole("button", { name: "Remove the Updated filter" })[0]);
    expect(onChange).toHaveBeenLastCalledWith([range[1]]);
  });
});
