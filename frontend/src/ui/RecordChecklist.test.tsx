import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { RecordChecklist, type ChecklistRecord } from "@/ui/RecordChecklist";

afterEach(() => vi.restoreAllMocks());

const names = (group: HTMLElement) =>
  within(group)
    .getAllByRole("checkbox")
    .map((box) => box.closest("label")?.textContent);

describe("the record checklist (0.9 K6a)", () => {
  it("lists given records with their hints, searched in place, the ticked pinned on top", () => {
    const onChange = vi.fn();
    const records: ChecklistRecord[] = [
      { id: "a", name: "Alpha", objectTypeKey: "domain", hint: "on 3 of 12" },
      { id: "b", name: "Bravo", objectTypeKey: "domain", hint: "on 1 of 12" },
    ];
    render(
      <RecordChecklist
        model={testModel}
        label="Domains"
        objectTypeKeys={["domain"]}
        records={records}
        chosen={[records[1]]}
        onChange={onChange}
      />,
    );
    const list = screen.getByRole("group", { name: "Domains" });
    expect(names(list)).toEqual(["Bravoon 1 of 12", "Alphaon 3 of 12"]);
    expect(screen.getByText("1 selected")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "Search domains" }), { target: { value: "alp" } });
    expect(names(list)).toEqual(["Alphaon 3 of 12"]);
    fireEvent.click(within(list).getByRole("checkbox"));
    expect(onChange).toHaveBeenLastCalledWith([records[1], records[0]]);
  });

  it("searches several types and lists them under a heading each", async () => {
    vi.spyOn(api, "objects").mockImplementation(async (type) => ({
      items: [type === "domain" ? { ...domainObject, name: "Delivery" } : { ...codelistObject, name: "Colours" }],
      nextCursor: null,
    }));
    render(
      <RecordChecklist
        model={testModel}
        label="Records"
        objectTypeKeys={["domain", "codelist"]}
        chosen={[]}
        onChange={vi.fn()}
      />,
    );
    expect(await screen.findByText("Domains")).toHaveClass("record-checklist-heading");
    expect(screen.getByText("Codelists")).toHaveClass("record-checklist-heading");
    expect(screen.getByText("Delivery")).toBeInTheDocument();
    expect(screen.getByText("Colours")).toBeInTheDocument();
  });
});

describe("a checklist for a relationship's candidates (0.9 K7)", () => {
  it("searches only the records the relationship may choose", async () => {
    const objects = vi.spyOn(api, "objects").mockResolvedValue({ items: [domainObject], nextCursor: null });
    render(
      <RecordChecklist
        model={testModel}
        label="Domains"
        objectTypeKeys={["domain"]}
        candidates={{ candidateFor: "codelist-belongs-to-domain", anchorTypeKey: "codelist" }}
        chosen={[]}
        onChange={vi.fn()}
      />,
    );
    expect(await screen.findByText(domainObject.name)).toBeInTheDocument();
    expect(objects).toHaveBeenCalledWith(
      "domain",
      expect.objectContaining({ candidateFor: "codelist-belongs-to-domain", anchorTypeKey: "codelist" }),
    );
  });
});
