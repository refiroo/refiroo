import { describe, expect, it } from "vitest";
import { bulkSelectionFor } from "@/features/objects/SelectionBar";
import { capabilitiesFixture } from "@/test/capabilities";

describe("bulkSelectionFor (0.9 K1, D105)", () => {
  it("lets records be selected only where data can be written and jobs created", () => {
    const capabilities = capabilitiesFixture();
    expect(bulkSelectionFor(capabilities, false)).toEqual({ maxItems: 1000000 });
    // A publication, or another read-only context.
    expect(bulkSelectionFor(capabilities, true)).toBeUndefined();
    const jobsOff = { ...capabilities, integrationJobs: { ...capabilities.integrationJobs, createJobs: false } };
    expect(bulkSelectionFor(jobsOff, false)).toBeUndefined();
    expect(bulkSelectionFor(undefined, false)).toBeUndefined();
  });
});
