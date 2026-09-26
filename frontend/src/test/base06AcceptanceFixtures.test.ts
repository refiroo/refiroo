import { describe, expect, it } from "vitest";
import { base06AcceptanceFixtures as fixtures } from "@/test/base06AcceptanceFixtures";

describe("Base 0.6 acceptance fixtures", () => {
  it("defines each ADR-024 journey exactly once and in plan order", () => {
    expect(fixtures.journeys.map((journey) => journey.id)).toEqual(["J1", "J2", "J3", "J4", "J5", "J6", "J7"]);
    expect(fixtures.journeys.every((journey) => journey.actions.length > 0 && journey.observe.length > 0)).toBe(true);
  });
  it("uses one workspace graph containing object types, containment and relations", () => {
    const graph = fixtures.publications.publication4.graph;
    expect(new Set(graph.objects.map((object) => object.objectTypeKey)).size).toBeGreaterThan(1);
    expect(graph.objects.some((object) => object.parentObjectId !== null)).toBe(true);
    expect(graph.relations).toHaveLength(2);
    expect(graph.relations.map((relation) => relation.kind).sort()).toEqual(["containment", "independent"]);
  });
  it("keeps workspace lineage and withdrawal separate from individual records", () => {
    expect(fixtures.publications.publication5.derivedFromPublicationId).toBe(fixtures.publications.publication3.id);
    expect(fixtures.publications.publication5.supersedesPublicationId).toBe(fixtures.publications.publication4.id);
    expect(fixtures.publications.publication5.derivedFromPublicationId).not.toBe(
      fixtures.publications.publication5.supersedesPublicationId,
    );
    expect(fixtures.publications.publication5.publicationState).toBe("inactive");
    expect(fixtures.publish.outcome).toEqual({
      publicationId: fixtures.publications.publication5.id,
      publicationState: "active",
    });
    expect(fixtures.publicationWithdrawal.after).toMatchObject({
      activePublicationId: null,
      workspaceIdentityRetained: true,
      objectIdentitiesRetained: true,
    });
    const withdrawalJourney = fixtures.journeys.find((journey) => journey.id === "J6");
    expect(withdrawalJourney?.title).not.toMatch(/restore/i);
    expect(withdrawalJourney?.observe).toContain("live data and immutable publications remain available");
  });
  it("preserves change set input for every workspace-level conflict", () => {
    expect(Object.values(fixtures.conflicts).every((conflict) => conflict.preserve.length > 0)).toBe(true);
    expect(fixtures.errors.cursorInvalid).toBe("workspace_cursor_invalid");
    expect(fixtures.cursors.invalidatedBy).toBe("publication_changed");
  });
});
