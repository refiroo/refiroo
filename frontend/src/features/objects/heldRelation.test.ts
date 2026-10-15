import { describe, expect, it, vi } from "vitest";
import { heldRelation } from "@/features/objects/useCellEditing";
import type { ObjectItem, RelationItem } from "@/types";

const item = { id: "item-1", workspaceKey: "west" } as ObjectItem;
const held = (id: string, type: string) =>
  ({ relation: { id }, object: { id: `${id}-end`, objectTypeKey: type } }) as RelationItem;

describe("heldRelation (0.10 R-F4)", () => {
  it("reads on past the relationships to another type until it finds the column's", async () => {
    // One relation type joins an item to many tags and to one zone; the column is the zone's.
    const read = vi.fn(async (_id: string, options?: { cursor?: string }) =>
      options?.cursor
        ? { items: [held("r9", "zone")], nextCursor: null }
        : { items: [held("b1", "tag"), held("b2", "tag")], nextCursor: "more" },
    );
    const edit = {
      relationTypeKey: "placed",
      direction: "outgoing",
      single: true,
      choices: [{ otherObjectTypeKey: "zone", label: "Zone" }],
    } as never;
    expect((await heldRelation(read as never, item, edit))?.relation.id).toBe("r9");
    expect(read).toHaveBeenCalledTimes(2);
  });
});
