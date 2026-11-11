import { render, renderHook, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { DraftMigrationNotice, useDraftMigration } from "@/features/model-editor/DraftMigration";
import type { DraftMigration, ModelDraftOutline } from "@/types";

vi.mock("@/api/client", () => ({ api: { modelDraftMigration: vi.fn() } }));

const migrationFor = (moved: number) => ({ landing: { moved } }) as unknown as DraftMigration;

describe("useDraftMigration (R13-F22)", () => {
  beforeEach(() => vi.clearAllMocks());

  it("is pending until read, and forgets the figures of another workspace", async () => {
    vi.mocked(api.modelDraftMigration).mockImplementation((_draft, workspace) =>
      workspace === "north" ? Promise.resolve(migrationFor(5)) : new Promise(() => undefined),
    );
    const { result, rerender } = renderHook(({ workspace }) => useDraftMigration("d1", workspace, true, 1), {
      initialProps: { workspace: "north" },
    });
    expect(result.current.pending).toBe(true);
    await waitFor(() => expect(result.current.migration?.landing?.moved).toBe(5));
    expect(result.current.pending).toBe(false);
    rerender({ workspace: "south" });
    expect(result.current.migration).toBeUndefined();
    expect(result.current.pending).toBe(true);
  });

  it("holds the read error for what it was read for only", async () => {
    vi.mocked(api.modelDraftMigration).mockImplementation((_draft, workspace) =>
      workspace === "north" ? Promise.reject(new Error("gone")) : new Promise(() => undefined),
    );
    const { result, rerender } = renderHook(({ workspace }) => useDraftMigration("d1", workspace, true, 1), {
      initialProps: { workspace: "north" },
    });
    await waitFor(() => expect(result.current.error).toBe("gone"));
    expect(result.current.pending).toBe(false);
    rerender({ workspace: "south" });
    expect(result.current.error).toBe("");
  });
});

describe("DraftMigrationNotice notes (0.13 R)", () => {
  it("lists a note each, however many steps raised the same one, without a duplicate key", () => {
    const note = { code: "MODEL_REPLACED", message: "A step replaced the whole model" };
    const migration = {
      steps: [{ step: 1 }, { step: 2 }],
      rows: [],
      splits: [],
      listConversions: [],
      relationTypeMappings: [],
      keyChanges: [],
      notes: [note, note],
    } as unknown as DraftMigration;
    render(
      <DraftMigrationNotice
        migration={migration}
        outline={{ applications: [] } as unknown as ModelDraftOutline}
        label="North"
      />,
    );
    expect(screen.getAllByText(/A step replaced the whole model/).length).toBeGreaterThan(0);
    // A duplicate key would be a console error, which fails the test (`test/consoleGuard`).
  });
});
