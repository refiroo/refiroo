import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { FilterBar, filterFields, pillText } from "@/features/objects/filters/FilterBar";
import { domainObject, testModel } from "@/test/fixtures";
import type { CollectionFilter, EngineModel } from "@/types";

afterEach(() => vi.restoreAllMocks());

const relation = "related:codelist-belongs-to-domain";
/** The test model with a number and a date to filter by, besides its text and yes/no. */
const model: EngineModel = {
  ...testModel,
  attributeTypes: [
    ...testModel.attributeTypes,
    { key: "count", name: "Count", valueType: "integer", features: {} },
    { key: "date", name: "Date", valueType: "date", features: {} },
  ] as EngineModel["attributeTypes"],
};
const fields = filterFields(model, ["code", "active", "count", "date", relation]);
const names = new Map([["d1", { id: "d1", name: "Delivery Methods", objectTypeKey: "domain" }]]);

function bar(filters: CollectionFilter[], onChange = vi.fn(), countDraft = vi.fn(async () => 3)) {
  render(
    <FilterBar
      model={model}
      objectTypeKey="codelist"
      fields={fields}
      filters={filters}
      names={names}
      noun={["Codelist", "Codelists"]}
      countDraft={countDraft}
      onChange={onChange}
    />,
  );
  return { onChange, countDraft };
}

async function addFilter(field: string) {
  fireEvent.click(screen.getByRole("button", { name: "Filter" }));
  const menu = await screen.findByRole("dialog", { name: "Filter" });
  fireEvent.click(within(menu).getByRole("button", { name: new RegExp(`^${field}`) }));
  return screen.findByLabelText(`Filter by ${field}`);
}

describe("the filter bar's pills (0.9 K6a, D160)", () => {
  it("shows each active filter as one pill, a relationship's records together, with × and Clear all", () => {
    const { onChange } = bar([
      { field: "code", operator: "startsWith", value: "CLI" },
      { field: "active", operator: "eq", value: "true" },
      { field: relation, operator: "eq", value: "d1" },
    ]);
    const pills = within(screen.getByRole("group", { name: "Filters" }));
    expect(pills.getByRole("button", { name: /^Code starts with: CLI/ })).toBeInTheDocument();
    expect(pills.getByRole("button", { name: /^Active: Yes/ })).toBeInTheDocument();
    expect(pills.getByRole("button", { name: /^Belongs to: Delivery Methods/ })).toBeInTheDocument();
    fireEvent.click(pills.getByRole("button", { name: "Remove the Code filter" }));
    expect(onChange).toHaveBeenLastCalledWith([
      { field: "active", operator: "eq", value: "true" },
      { field: relation, operator: "eq", value: "d1" },
    ]);
    fireEvent.click(pills.getByRole("button", { name: "Clear all" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it("words every condition a pill can hold", () => {
    const spec = (field: string) => fields.find((item) => item.field === field)!;
    expect(pillText(spec("count"), [{ field: "count", operator: "gte", value: "5" }], names)).toEqual({
      label: "Count at least",
      value: "5",
    });
    expect(pillText(spec("date"), [{ field: "date", operator: "lt", value: "2026-01-01" }], names)).toEqual({
      label: "Date before",
      value: "2026-01-01",
    });
    expect(pillText(spec("code"), [{ field: "code", operator: "isNull", value: "false" }], names).value).toBe(
      "has a value",
    );
    expect(pillText(spec("code"), [{ field: "code", operator: "isUnset", value: "true" }], names).value).toBe(
      "not set",
    );
    expect(pillText(spec(relation), [{ field: relation, operator: "isNull", value: "true" }], names).value).toBe(
      "none",
    );
  });
});

describe("the field menu (0.9 K6a, D164)", () => {
  it("groups the fields, marks the applied one, and has no search with eight or fewer", async () => {
    bar([{ field: "active", operator: "eq", value: "true" }]);
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const menu = await screen.findByRole("dialog", { name: "Filter" });
    expect(within(menu).getByRole("group", { name: "Fields" })).toBeInTheDocument();
    expect(
      within(within(menu).getByRole("group", { name: "Relationships" })).getByRole("button", { name: "Belongs to" }),
    ).toBeInTheDocument();
    expect(within(menu).getByRole("button", { name: "Active, applied" })).toBeInTheDocument();
    expect(within(menu).queryByRole("searchbox")).toBeNull();
    await waitFor(() => expect(within(menu).getAllByRole("button")[0]).toHaveFocus());
  });
});

describe("the editors (0.9 K6a, D161, D162)", () => {
  it("offers a text field's common conditions and the rest under More, applying with Apply only", async () => {
    const { onChange } = bar([]);
    const editor = await addFilter("Code");
    expect(
      within(editor)
        .getAllByRole("radio")
        .map((radio) => radio.closest("label")?.textContent),
    ).toEqual(["Contains", "Is", "Starts with"]);
    expect(
      within(within(editor).getByRole("combobox", { name: "More conditions for Code" }))
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["More", "Is empty", "Has a value", "Not set", "Is set"]);
    fireEvent.change(within(editor).getByRole("textbox", { name: "Code" }), { target: { value: "  CLI " } });
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.click(within(editor).getByRole("button", { name: "Apply" }));
    expect(onChange).toHaveBeenLastCalledWith([{ field: "code", operator: "contains", value: "CLI" }]);
  });

  it("offers a number's and a date's comparisons in their own words", async () => {
    bar([]);
    let editor = await addFilter("Count");
    expect(
      within(editor)
        .getAllByRole("radio")
        .map((radio) => radio.closest("label")?.textContent),
    ).toEqual(["Is", "Less than", "More than"]);
    fireEvent.click(within(editor).getByRole("button", { name: "Cancel" }));
    fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" });
    editor = await addFilter("Date");
    expect(
      within(editor)
        .getAllByRole("radio")
        .map((radio) => radio.closest("label")?.textContent),
    ).toEqual(["Is", "Before", "After"]);
    expect(within(editor).getByRole("combobox", { name: "More conditions for Date" })).toHaveTextContent("On or after");
  });

  it("applies yes or no as it is chosen", async () => {
    const { onChange } = bar([]);
    const editor = await addFilter("Active");
    fireEvent.click(within(editor).getByRole("radio", { name: "No" }));
    expect(onChange).toHaveBeenLastCalledWith([{ field: "active", operator: "eq", value: "false" }]);
  });

  it("ticks a relationship's records in a checklist and applies them once; none and any need no records", async () => {
    vi.spyOn(api, "objects").mockResolvedValue({
      items: [
        { ...domainObject, id: "d1", name: "Delivery Methods" },
        { ...domainObject, id: "d2", name: "Payment Methods" },
      ],
      nextCursor: null,
    });
    const { onChange } = bar([]);
    const editor = await addFilter("Belongs to");
    const list = await within(editor).findByRole("group", { name: "Domains" });
    fireEvent.click(within((await within(list).findByText("Payment Methods")).closest("label")!).getByRole("checkbox"));
    fireEvent.click(
      within((await within(list).findByText("Delivery Methods")).closest("label")!).getByRole("checkbox"),
    );
    expect(within(editor).getByText("2 selected")).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.click(within(editor).getByRole("button", { name: "Apply" }));
    expect(onChange).toHaveBeenLastCalledWith([
      { field: relation, operator: "eq", value: "d2" },
      { field: relation, operator: "eq", value: "d1" },
    ]);
  });
});
