import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { criteriaFromFilters } from "@/features/jobs/exportRequest";
import { ObjectToolbar } from "@/features/objects/ObjectToolbar";
import { relationFilterEntries, relationFilterMode, relationFilterText } from "@/features/objects/RelationFilter";
import { codelistObject, testModel } from "@/test/fixtures";
import type { CollectionQueryState, TableViewDefinition } from "@/types";

afterEach(() => vi.restoreAllMocks());

const field = "related:codelist-belongs-to-domain";
const view: TableViewDefinition = {
  key: "codelists",
  name: "Codelists",
  type: "table",
  objectTypeKey: "codelist",
  config: {
    columns: ["name", field],
    filterFields: ["code", field],
    sortFields: ["name"],
    defaultSort: "name",
    pageSize: 20,
  },
};
const query = (filters: CollectionQueryState["filters"]): CollectionQueryState =>
  ({ search: "", filters, sort: "name", pageSize: 20 }) as CollectionQueryState;

describe("a relationship filter's entries (0.9 K6, D153, D158)", () => {
  it("stores one eq per chosen record, or one isNull, and reads its mode back", () => {
    const chosen = [
      { id: "a", name: "Alpha" },
      { id: "b", name: "Bravo" },
    ];
    expect(relationFilterEntries(field, "any", chosen)).toEqual([
      { field, operator: "eq", value: "a" },
      { field, operator: "eq", value: "b" },
    ]);
    expect(relationFilterEntries(field, "none", chosen)).toEqual([{ field, operator: "isNull", value: "true" }]);
    expect(relationFilterEntries(field, "some", [])).toEqual([{ field, operator: "isNull", value: "false" }]);
    expect(relationFilterMode(relationFilterEntries(field, "none", []))).toBe("none");
    expect(relationFilterMode(relationFilterEntries(field, "any", chosen))).toBe("any");
    const names = new Map([["a", { id: "a", name: "Alpha", objectTypeKey: "domain" }]]);
    expect(relationFilterText(relationFilterEntries(field, "any", chosen), names)).toBe("is any of Alpha, …");
    expect(relationFilterText(relationFilterEntries(field, "some", []), names)).toBe("has any");
  });

  it("becomes the query's related hop in an export, as the list applies it", () => {
    const criteria = criteriaFromFilters(testModel, [
      { field: "code", operator: "eq", value: "X" },
      ...relationFilterEntries(field, "any", [
        { id: "a", name: "Alpha" },
        { id: "b", name: "Bravo" },
      ]),
    ]);
    expect(criteria).toEqual([
      {
        related: {
          relationTypeKey: "domain-contains-codelist",
          direction: "incoming",
          where: [
            { field: "id", op: "eq", value: "a" },
            { field: "id", op: "eq", value: "b" },
          ],
        },
      },
      { field: "code", op: "eq", value: "X" },
    ]);
    expect(criteriaFromFilters(testModel, relationFilterEntries(field, "none", []))).toEqual([
      { related: { relationTypeKey: "domain-contains-codelist", direction: "incoming", where: [] }, not: true },
    ]);
  });
});

describe("the toolbar's relationship filter (0.9 K6)", () => {
  it("offers its modes, applies has none, and names the chosen records on the chip after a reload", async () => {
    const read = vi.spyOn(api, "objects").mockResolvedValue({
      items: [{ ...codelistObject, id: "d1", name: "Delivery Methods", objectTypeKey: "domain" }],
      nextCursor: null,
    });
    const onChange = vi.fn();
    render(
      <ObjectToolbar
        model={testModel}
        view={view}
        query={query([{ field, operator: "eq", value: "d1" }])}
        placeholder="Search codelists"
        onChange={onChange}
        display={null}
      />,
    );
    // The chip reads the chosen record's name back by its ID.
    await screen.findByRole("button", { name: "Remove Belongs to is any of Delivery Methods" });
    expect(read.mock.calls[0][0]).toBe("domain");
    expect(read.mock.calls[0][1].filters).toEqual([{ field: "id", operator: "eq", value: "d1" }]);

    fireEvent.click(screen.getByRole("button", { name: /Filter/ }));
    const operator = await screen.findByRole("combobox", { name: "Belongs to operator" });
    expect(
      within(operator)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["is any of", "has none", "has any"]);
    fireEvent.change(operator, { target: { value: "none" } });
    await waitFor(() => expect(onChange).toHaveBeenCalled());
    expect(onChange.mock.calls.at(-1)?.[0].filters).toEqual([{ field, operator: "isNull", value: "true" }]);
  });
});
