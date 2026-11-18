import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { RELATED_FIELD_PREFIX, relatedCellEdit } from "@/model/lookup";
import type { EngineModel } from "@/types";
import { RelatedRecordsDialog } from "@/features/objects/RelatedRecordsDialog";

vi.mock("@/api/client", () => ({
  api: { relations: vi.fn(), objects: vi.fn(), runBatch: vi.fn() },
}));

// A relation type with two bindings from "domain", only one of which the record's own end may meet.
const model: EngineModel = {
  ...testModel,
  relationTypes: [
    ...testModel.relationTypes,
    {
      key: "domain-cites",
      reverseKey: "cited-by-domain",
      name: "Cites",
      reverseName: "Cited by",
      isOriented: true,
      features: {},
    },
  ],
  objectTypeRelations: [
    ...testModel.objectTypeRelations,
    {
      relationTypeKey: "domain-cites",
      fromObjectTypeKey: "domain",
      toObjectTypeKey: "codelist",
      cardinality: "many-to-many",
      candidates: { from: [{ field: "name", op: "startsWith", value: "Res" }] },
    },
    {
      relationTypeKey: "domain-cites",
      fromObjectTypeKey: "domain",
      toObjectTypeKey: "domain",
      cardinality: "many-to-many",
      candidates: { from: [{ field: "name", op: "startsWith", value: "Zzz" }] },
    },
  ],
};
const edit = relatedCellEdit(model, "domain", `${RELATED_FIELD_PREFIX}domain-cites`)!;

describe("RelatedRecordsDialog own end (0.9 K7, D172)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.relations).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.objects).mockImplementation(async (type, options) => {
      const check = (options as { filters?: unknown }).filters !== undefined;
      // The own-end check passes for the binding to codelists only.
      if (check) {
        const anchor = (options as { anchorTypeKey?: string }).anchorTypeKey;
        return { items: anchor === "codelist" ? [domainObject] : [], nextCursor: null };
      }
      return { items: type === "codelist" ? [codelistObject] : [], nextCursor: null };
    });
  });

  it("offers only the types whose binding the record meets", async () => {
    render(
      <RelatedRecordsDialog model={model} object={domainObject} edit={edit} onClose={vi.fn()} onSaved={vi.fn()} />,
    );
    expect(await screen.findByText(codelistObject.name)).toBeInTheDocument();
    const searched = vi
      .mocked(api.objects)
      .mock.calls.filter(([, options]) => !(options as { filters?: unknown }).filters);
    expect(searched.map(([type]) => type)).toEqual(["codelist"]);
  });

  it("says why when the record meets no binding, and offers no list to search", async () => {
    vi.mocked(api.objects).mockResolvedValue({ items: [], nextCursor: null });
    render(
      <RelatedRecordsDialog model={model} object={domainObject} edit={edit} onClose={vi.fn()} onSaved={vi.fn()} />,
    );
    expect(await screen.findAllByText(/can have this relationship/)).toHaveLength(2);
    expect(
      vi.mocked(api.objects).mock.calls.every(([, options]) => Boolean((options as { filters?: unknown }).filters)),
    ).toBe(true);
    expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
  });
});
