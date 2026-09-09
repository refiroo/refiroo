import { describe, expect, it } from "vitest";
import { base06AcceptanceFixtures as fixtures } from "@/test/base06AcceptanceFixtures";

describe("Base 0.6 acceptance fixtures", () => {
  it("defines each ADR-024 journey exactly once and in plan order", () => {
    expect(fixtures.journeys.map((journey) => journey.id)).toEqual(["J1", "J2", "J3", "J4", "J5", "J6", "J7"]);
    expect(fixtures.journeys.every((journey) => journey.actions.length > 0 && journey.observe.length > 0)).toBe(true);
  });
  it("uses one workspace graph containing object types, containment and relations", () => {
    const graph = fixtures.revisions.revision4.graph;
    expect(new Set(graph.objects.map((object) => object.objectTypeKey)).size).toBeGreaterThan(1);
    expect(graph.objects.some((object) => object.parentObjectId !== null)).toBe(true);
    expect(graph.relations).toHaveLength(2);
    expect(graph.relations.map((relation) => relation.kind).sort()).toEqual(["containment", "independent"]);
  });
  it("keeps workspace lineage and retirement separate from individual records", () => {
    expect(fixtures.revisions.revision5.derivedFromRevisionId).toBe(fixtures.revisions.revision3.id);
    expect(fixtures.revisions.revision5.supersedesRevisionId).toBe(fixtures.revisions.revision4.id);
    expect(fixtures.revisions.revision5.derivedFromRevisionId).not.toBe(
      fixtures.revisions.revision5.supersedesRevisionId,
    );
    expect(fixtures.revisions.revision5.publicationState).toBe("inactive");
    expect(fixtures.activation.outcome).toEqual({
      revisionId: fixtures.revisions.revision5.id,
      publicationState: "active",
    });
    expect(fixtures.publicationRetirement.after).toMatchObject({
      activeRevisionId: null,
      workspaceIdentityRetained: true,
      objectIdentitiesRetained: true,
    });
    const retirementJourney = fixtures.journeys.find((journey) => journey.id === "J6");
    expect(retirementJourney?.title).not.toMatch(/restore/i);
    expect(retirementJourney?.observe).toContain("live data and immutable history remain available");
  });
  it("preserves draft input for every workspace-level conflict", () => {
    expect(Object.values(fixtures.conflicts).every((conflict) => conflict.preserve.length > 0)).toBe(true);
    expect(fixtures.errors.cursorInvalid).toBe("workspace_cursor_invalid");
    expect(fixtures.cursors.invalidatedBy).toBe("workspace_revision_changed");
  });
});
