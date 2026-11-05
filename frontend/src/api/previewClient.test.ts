import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import {
  createPreviewClient,
  emptyRecord,
  PREVIEW_EMPTY_ID,
  PreviewWriteRefused,
  relaxedPickerRelations,
} from "@/api/previewClient";
import type { EngineModel, ObjectTypeRelationDefinition } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const binding = (from: string, to: string, candidates?: ObjectTypeRelationDefinition["candidates"]) => ({
  relationTypeKey: "sold-through",
  fromObjectTypeKey: from,
  toObjectTypeKey: to,
  cardinality: "many-to-many" as const,
  ...(candidates ? { candidates } : {}),
});

function model(types: Record<string, string[]>, relations: ObjectTypeRelationDefinition[]): EngineModel {
  return {
    attributeTypes: [],
    objectTypes: Object.entries(types).map(([key, attributes]) => ({
      key,
      name: key,
      pluralName: key,
      attributes: attributes.map((attributeTypeKey, index) => ({
        attributeTypeKey,
        required: false,
        readOnly: false,
        order: index,
        ui: {},
      })),
      features: {},
      behavior: {},
      validation: {},
    })),
    relationTypes: [
      {
        key: "sold-through",
        reverseKey: "sells",
        name: "Sold through",
        reverseName: "Sells",
        isOriented: true,
        features: {},
      },
    ],
    objectTypeRelations: relations,
    applications: [],
  } as unknown as EngineModel;
}

const active = model({ item: ["code"], channel: [] }, [binding("item", "channel")]);
const page = { items: [], nextCursor: null };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.objects).mockResolvedValue(page);
});

describe("the preview's client", () => {
  it("refuses every write before a request is sent", async () => {
    const client = createPreviewClient(active, active);
    for (const call of [
      () => client.createRelation({} as never),
      () => client.updateAttribute("item", "1", "code", "x", 1),
      () => client.deleteObject("item", "1", 1),
      () => client.applyModelDraftOperations("d1", 1, []),
    ])
      await expect(call()).rejects.toBeInstanceOf(PreviewWriteRefused);
    expect(api.createRelation).not.toHaveBeenCalled();
    expect(api.updateAttribute).not.toHaveBeenCalled();
    expect(api.deleteObject).not.toHaveBeenCalled();
  });

  it("answers the empty record and what it holds without the server", async () => {
    const sample = emptyRecord("catalogue", "pack", "default");
    const client = createPreviewClient(active, active, sample);
    await expect(client.object("pack", PREVIEW_EMPTY_ID, "default")).resolves.toMatchObject({ id: PREVIEW_EMPTY_ID });
    await expect(client.relations(PREVIEW_EMPTY_ID)).resolves.toMatchObject({ items: [] });
    await expect(client.objects("item", { parentObjectId: PREVIEW_EMPTY_ID })).resolves.toMatchObject({ items: [] });
    expect(api.object).not.toHaveBeenCalled();
    expect(api.relations).not.toHaveBeenCalled();
    expect(api.objects).not.toHaveBeenCalled();
  });

  it("lists nothing for a type the active model does not hold", async () => {
    const draft = model({ item: ["code"], channel: [], pack: [] }, [binding("item", "channel")]);
    await expect(createPreviewClient(active, draft).objects("pack", {})).resolves.toMatchObject({ items: [] });
    expect(api.objects).not.toHaveBeenCalled();
  });

  it("leaves out a sort, filter or relation column the active type lacks", async () => {
    const draft = model({ item: ["code", "pack-size"], channel: [] }, [binding("item", "channel")]);
    await createPreviewClient(active, draft).objects("item", {
      sort: "-pack-size",
      filters: [
        { field: "pack-size", op: "eq", value: 2 },
        { field: "code", op: "eq", value: "A" },
      ] as never,
      expand: ["sold-through", "packed-in"],
    });
    expect(api.objects).toHaveBeenCalledWith(
      "item",
      expect.objectContaining({
        sort: undefined,
        filters: [{ field: "code", op: "eq", value: "A" }],
        expand: ["sold-through"],
      }),
    );
  });

  it("keeps a relation column showing a field the active model answers, and leaves out one it cannot", async () => {
    const known = { ...active, attributeTypes: [{ key: "code" }] } as unknown as EngineModel;
    await createPreviewClient(known, known).objects("item", {
      expand: [
        "sold-through.code",
        "sold-through.ancestor:channel.code",
        "sells.name",
        "sold-through.pack-size",
        "sold-through.ancestor:region.code",
      ],
    });
    expect(api.objects).toHaveBeenCalledWith(
      "item",
      expect.objectContaining({
        expand: ["sold-through.code", "sold-through.ancestor:channel.code", "sells.name"],
      }),
    );
  });

  it("applies a picker's choice rule the active model holds, and not one the draft changes (D45)", async () => {
    const rule = { to: [{ field: "code", op: "eq", value: "web" }] };
    const kept = model({ item: ["code"], channel: [] }, [binding("item", "channel")]);
    await createPreviewClient(active, kept).objects("channel", { candidateFor: "sold-through", anchorTypeKey: "item" });
    expect(api.objects).toHaveBeenLastCalledWith(
      "channel",
      expect.objectContaining({ candidateFor: "sold-through", anchorTypeKey: "item" }),
    );

    const changed = model({ item: ["code"], channel: [] }, [binding("item", "channel", rule)]);
    expect(relaxedPickerRelations(active, changed, "item")).toEqual(["sold-through"]);
    await createPreviewClient(active, changed).objects("channel", {
      candidateFor: "sold-through",
      anchorTypeKey: "item",
    });
    expect(vi.mocked(api.objects).mock.lastCall?.[1]).not.toHaveProperty("candidateFor");
  });

  it("relaxes a relation the draft allows anew, and not one it keeps", () => {
    const draft = model({ item: ["code"], channel: [], shop: [] }, [
      binding("item", "channel"),
      binding("shop", "channel"),
    ]);
    expect(relaxedPickerRelations(active, draft, "item")).toEqual([]);
    expect(relaxedPickerRelations(active, draft, "shop")).toEqual(["sold-through"]);
  });
});
