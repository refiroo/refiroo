import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import type { RelationChoice } from "@/model/lookup";
import { RelationFormDialog } from "@/features/objects/panels/RelationFormDialog";

vi.mock("@/api/client", () => ({
  api: { createRelation: vi.fn(), objects: vi.fn(), relations: vi.fn() },
}));

const relation = testModel.objectTypeRelations[0];
const contains: RelationChoice = {
  direction: "outgoing",
  relation,
  otherObjectTypeKey: "codelist",
  label: "Contains",
};
const alsoMentions: RelationChoice = { ...contains, otherObjectTypeKey: "domain", label: "Mentions" };

describe("RelationFormDialog (0.17 PL2)", () => {
  beforeEach(() => {
    vi.mocked(api.createRelation).mockReset();
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
  });
  afterEach(() => vi.restoreAllMocks());

  function open(choices: RelationChoice[]) {
    const onSaved = vi.fn();
    render(
      <RelationFormDialog
        model={testModel}
        object={domainObject}
        choices={choices}
        onClose={vi.fn()}
        onSaved={onSaved}
      />,
    );
    return { onSaved };
  }

  it("says the relationship it adds as a sentence where it is known, with no select", async () => {
    open([contains]);
    const dialog = screen.getByRole("dialog", { name: "Add Codelist" });
    expect(dialog).toHaveTextContent(`Add a Codelist to ${domainObject.name}`);
    expect(dialog).not.toHaveTextContent(/\(outgoing\)|object|Create relationship/i);
    expect(screen.queryByRole("combobox", { name: "What to add" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Codelist" })).toHaveClass("primary");
  });

  it("keeps the choice where the relationship is not known, without directions in its words", () => {
    open([contains, alsoMentions]);
    const select = screen.getByRole("combobox", { name: "What to add" });
    expect(Array.from((select as HTMLSelectElement).options).map((option) => option.text)).toEqual([
      "Codelist (Contains)",
      "Domain (Mentions)",
    ]);
    expect(screen.queryByText(/outgoing|incoming/)).not.toBeInTheDocument();
  });

  it("adds the chosen record", async () => {
    vi.mocked(api.createRelation).mockResolvedValue({} as never);
    const other = { ...domainObject, id: "22222222-2222-4222-8222-222222222222", name: "Financial" };
    vi.mocked(api.objects).mockResolvedValue({ items: [other], nextCursor: null });
    const { onSaved } = open([contains]);
    fireEvent.click(await screen.findByRole("option", { name: /Financial/ }));
    fireEvent.click(screen.getByRole("button", { name: "Add Codelist" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(api.createRelation).toHaveBeenCalledWith(
      expect.objectContaining({ relationTypeKey: relation.relationTypeKey, fromObjectId: domainObject.id }),
    );
  });
});
