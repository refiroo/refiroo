import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { schemaLanguages, useSystem } from "@/state/useSystem";

vi.mock("@/api/client", () => ({ api: { system: vi.fn() } }));

const system = (active: string) =>
  ({ activeModelRelease: { name: active }, engine: {}, schemaLanguages: ["0.9"] }) as never;

describe("the system's parts", () => {
  it("reads the system fresh on every mount, so an activation shows at once", async () => {
    vi.mocked(api.system).mockResolvedValueOnce(system("Before")).mockResolvedValueOnce(system("After"));
    const first = renderHook(() => useSystem());
    await waitFor(() => expect(first.result.current.system?.activeModelRelease.name).toBe("Before"));
    first.unmount();
    const second = renderHook(() => useSystem());
    await waitFor(() => expect(second.result.current.system?.activeModelRelease.name).toBe("After"));
  });

  it("keeps only the static parts: the schema languages are read once", async () => {
    vi.mocked(api.system).mockClear();
    vi.mocked(api.system).mockResolvedValue(system("Any"));
    expect(await schemaLanguages()).toEqual(["0.9"]);
    expect(await schemaLanguages()).toEqual(["0.9"]);
    expect(api.system).toHaveBeenCalledTimes(1);
  });
});
