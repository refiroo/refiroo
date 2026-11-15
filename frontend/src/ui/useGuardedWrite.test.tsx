import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/api/errors";
import { changedWhileOpen, useGuardedWrite } from "./useGuardedWrite";

describe("changedWhileOpen (SR-D2)", () => {
  it("says it as one sentence for a record, a person and a panel that must be reloaded", () => {
    expect(changedWhileOpen("client")).toBe(
      "This client changed while the page was open. It is shown as it is now; review it and choose again.",
    );
    expect(changedWhileOpen("person", { they: true })).toBe(
      "This person changed while the page was open. They are shown as they are now; review it and choose again.",
    );
    expect(changedWhileOpen("workspace", { now: "It is now “West” and active." })).toBe(
      "This workspace changed while the page was open. It is now “West” and active. Review it and choose again.",
    );
  });
});

describe("useGuardedWrite", () => {
  it("keeps a stale version apart from any other refusal", async () => {
    const { result } = renderHook(() => useGuardedWrite());
    await act(() =>
      result.current.run(
        async () => {
          throw new ApiError(409, "VERSION_CONFLICT", "stale");
        },
        { onConflict: () => changedWhileOpen("client") },
      ),
    );
    expect(result.current.conflict).toContain("This client changed while the page was open.");
    expect(result.current.error).toBe("");
    await act(() =>
      result.current.run(
        async () => {
          throw new Error("Refused");
        },
        { onConflict: () => "never" },
      ),
    );
    expect(result.current.conflict).toBe("");
    expect(result.current.error).toBe("Refused");
    expect(result.current.pending).toBe(false);
  });
});

describe("useGuardedWrite handlers that throw", () => {
  it("still says the refusal when onRefused or onConflict throws", async () => {
    const { result } = renderHook(() => useGuardedWrite());
    await act(() =>
      result.current.run(
        async () => {
          throw new Error("Refused");
        },
        {
          onRefused: () => {
            throw new Error("reload failed");
          },
        },
      ),
    );
    expect(result.current.error).toBe("Refused");
    await act(() =>
      result.current.run(
        async () => {
          throw new ApiError(409, "VERSION_CONFLICT", "stale");
        },
        {
          onConflict: async () => {
            throw new Error("reload failed");
          },
        },
      ),
    );
    expect(result.current.error).toBe("stale");
    expect(result.current.pending).toBe(false);
  });
});
