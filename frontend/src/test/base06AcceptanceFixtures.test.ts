import { describe, expect, it } from "vitest";
import { base06AcceptanceFixtures as fixtures } from "@/test/base06AcceptanceFixtures";

describe("Base 0.6 acceptance fixtures", () => {
  it("defines each acceptance journey exactly once and in plan order", () => {
    expect(fixtures.journeys.map((journey) => journey.id)).toEqual(["J1", "J2", "J3", "J4", "J5", "J6", "J7"]);
  });

  it("backs every configured table filter and sort with an attribute capability", () => {
    const { table, attributeCapabilities } = fixtures.model;

    expect(attributeCapabilities["codelist-code"].features.filterable).toBe(true);
    expect(attributeCapabilities["codelist-code"].features.sortable).toBe(true);
    expect(attributeCapabilities.active.features.filterable).toBe(true);
    expect(table.filterFields).toEqual(["codelist-code", "active"]);
    expect(table.sortFields).toContain("codelist-code");
  });

  it("keeps the successful root Translation outside the existing active uniqueness scope", () => {
    const activeTarget = fixtures.revisions.translationRevision1.snapshot.requiredRelationships[0].otherObjectId;
    const rootTarget = fixtures.drafts.translationRoot.content.requiredRelationships[0].otherObjectId;

    expect(rootTarget).not.toBe(activeTarget);
    expect(fixtures.drafts.translationRoot.content.parentObjectId).toBe(
      fixtures.objects.parents.connectionsTranslationGroup.id,
    );
  });

  it("keeps derivation and activation supersession distinct when branching from history", () => {
    const transition = fixtures.transitions.activateDraftFromHistory;

    expect(transition.derivedFromRevisionId).toBe(fixtures.revisions.codelistRevision1.id);
    expect(transition.expectedSupersedesRevisionId).toBe(fixtures.revisions.codelistRevision2.id);
    expect(transition.derivedFromRevisionId).not.toBe(transition.expectedSupersedesRevisionId);
  });

  it("retires without deleting identity or history and preserves input for every conflict", () => {
    expect(fixtures.transitions.retireTranslation.after).toMatchObject({
      activeRevisionId: null,
      revisionLifecycle: "retired",
      logicalIdentityRetained: true,
      historyRetained: true,
    });

    expect(Object.values(fixtures.conflicts).every((conflict) => conflict.preserve.length > 0)).toBe(true);
  });
});
