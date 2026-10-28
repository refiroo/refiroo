import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import { HistoryPanel } from "@/features/objects/panels/HistoryPanel";
import { createPreviewClient, PREVIEW_EMPTY_ID } from "@/api/previewClient";
import { PreviewDataProvider } from "@/features/workspaces/WorkspaceDataContext";

vi.mock("@/api/client", () => ({ api: { objectHistory: vi.fn() } }));

describe("HistoryPanel", () => {
  it("loads bounded history pages independently", async () => {
    vi.mocked(api.objectHistory)
      .mockResolvedValueOnce({
        items: [
          {
            id: "event-2",
            aggregateType: "object",
            aggregateId: domainObject.id,
            action: "updated",
            version: 2,
            changedFields: ["name"],
            attributeTypeKeys: [],
            occurredAt: "2026-09-05T10:00:00Z",
            actor: { kind: "client", id: "c1", name: "Catalogue sync" },
          },
        ],
        nextCursor: "older",
      })
      .mockResolvedValueOnce({
        items: [
          {
            id: "event-1",
            aggregateType: "attribute",
            aggregateId: "attribute-id",
            action: "created",
            version: 1,
            changedFields: ["attributes"],
            attributeTypeKeys: ["code"],
            occurredAt: "2026-09-04T10:00:00Z",
            actor: null,
          },
        ],
        nextCursor: null,
      });
    render(<HistoryPanel objectTypeKey="domain" objectId={domainObject.id} />);
    expect(await screen.findByText("Record updated")).toBeInTheDocument();
    // The 10 newest first, then 20 more (0.12 RH1, D393).
    expect(api.objectHistory).toHaveBeenLastCalledWith("domain", domainObject.id, { pageSize: 10 });
    // Opened, an entry that kept names only says what changed and who made it (0.12 Z4, D320).
    fireEvent.click(screen.getByRole("button", { name: /Record updated/ }));
    expect(screen.getByText("Changed name")).toBeInTheDocument();
    expect(screen.getByText("by Catalogue sync (client)")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load older history" }));
    expect(await screen.findByText("Field value added")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Field value added/ }));
    expect(screen.getByText("Changed code")).toBeInTheDocument();
    expect(screen.getByText("Before sign-in")).toBeInTheDocument();
    await waitFor(() =>
      expect(api.objectHistory).toHaveBeenLastCalledWith("domain", domainObject.id, { cursor: "older", pageSize: 20 }),
    );
  });

  it("marks a change the AI proposed, with its confidence, its reason and who asked (0.16 AP2)", async () => {
    vi.mocked(api.objectHistory).mockResolvedValueOnce({
      items: [
        {
          id: "event-3",
          aggregateType: "relation",
          aggregateId: "relation-id",
          action: "created",
          version: 3,
          changedFields: [],
          attributeTypeKeys: [],
          occurredAt: "2026-09-05T10:00:00Z",
          actor: { kind: "user", id: "p1", name: "Ana Varga" },
          origin: {
            kind: "ai",
            provider: "fake",
            model: "fake-1",
            promptVersion: "1",
            confidence: 0.86,
            reason: "The name says so.",
            proposedBy: "p1",
          },
        },
      ],
      nextCursor: null,
    });
    render(<HistoryPanel objectTypeKey="domain" objectId={domainObject.id} />);
    fireEvent.click(await screen.findByRole("button", { name: /proposed by the AI/ }));
    expect(screen.getByText("Proposed by the AI assistant (fake-1), 86% confident")).toBeInTheDocument();
    expect(screen.getByText("The name says so. Asked for by Ana Varga.")).toBeInTheDocument();
  });

  it("retries the same older-history cursor after a paging failure", async () => {
    vi.mocked(api.objectHistory)
      .mockResolvedValueOnce({
        items: [
          {
            id: "event-2",
            aggregateType: "object",
            aggregateId: domainObject.id,
            action: "updated",
            version: 2,
            changedFields: ["name"],
            attributeTypeKeys: [],
            occurredAt: "2026-09-05T10:00:00Z",
            actor: null,
          },
        ],
        nextCursor: "older",
      })
      .mockRejectedValueOnce(new Error("History page unavailable"))
      .mockResolvedValueOnce({
        items: [
          {
            id: "event-1",
            aggregateType: "object",
            aggregateId: domainObject.id,
            action: "created",
            version: 1,
            changedFields: ["name"],
            attributeTypeKeys: [],
            occurredAt: "2026-09-04T10:00:00Z",
            actor: null,
          },
        ],
        nextCursor: null,
      });
    render(<HistoryPanel objectTypeKey="domain" objectId={domainObject.id} />);
    fireEvent.click(await screen.findByRole("button", { name: "Load older history" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Record created")).toBeInTheDocument();
    expect(api.objectHistory).toHaveBeenLastCalledWith("domain", domainObject.id, { cursor: "older", pageSize: 20 });
  });

  it("describes changes in model terms without exposing identifiers or concurrency tokens", async () => {
    vi.mocked(api.objectHistory).mockResolvedValueOnce({
      items: [
        {
          id: "event-3",
          aggregateType: "relation",
          aggregateId: "relation-id",
          action: "created",
          version: 1,
          changedFields: ["expectedChangeSetVersion", "fromObjectId", "relationTypeKey", "changeSetId"],
          attributeTypeKeys: [],
          occurredAt: "2026-09-05T10:00:00Z",
          actor: null,
        },
        {
          id: "event-4",
          aggregateType: "object",
          aggregateId: domainObject.id,
          action: "created",
          version: 1,
          changedFields: ["initialRelations", "objectTypeKey", "attributes"],
          attributeTypeKeys: ["code"],
          occurredAt: "2026-09-04T10:00:00Z",
          actor: null,
        },
      ],
      nextCursor: null,
    });
    render(<HistoryPanel model={testModel} objectTypeKey="domain" objectId={domainObject.id} />);
    expect(await screen.findByText("Relationship created")).toBeInTheDocument();
    expect(screen.getByText("Record created")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Record created/ }));
    expect(screen.getByText("Changed Code")).toBeInTheDocument();
    expect(screen.queryByText(/expectedChangeSetVersion|fromObjectId|initialRelations|objectTypeKey/)).toBeNull();
  });

  it("shows each value with the one before, and says where the one before was not recorded (0.12 RH1)", async () => {
    vi.mocked(api.objectHistory).mockResolvedValueOnce({
      items: [
        {
          id: "event-5",
          aggregateType: "object",
          aggregateId: domainObject.id,
          action: "updated",
          version: 3,
          changedFields: ["attributes", "name"],
          attributeTypeKeys: ["code"],
          occurredAt: "2026-09-06T10:00:00Z",
          actor: null,
          kind: "values",
          values: [
            { field: "name", kind: "name", from: "Old name", to: "New name", fromKnown: true },
            { field: "code", kind: "attribute", from: null, to: "C-2", fromKnown: false },
          ],
        },
      ],
      nextCursor: null,
    });
    render(<HistoryPanel model={testModel} objectTypeKey="domain" objectId={domainObject.id} />);
    fireEvent.click(await screen.findByRole("button", { name: /Name and Code changed/ }));
    expect(screen.getByText("Old name")).toBeInTheDocument();
    expect(screen.getByText("New name")).toBeInTheDocument();
    expect(screen.getByText("not recorded")).toBeInTheDocument();
    expect(screen.getByText("C-2")).toBeInTheDocument();
  });

  it("asks the API for one kind of change, and shows fewer again after loading older ones", async () => {
    const entry = (index: number) => ({
      id: `event-${index}`,
      aggregateType: "object",
      aggregateId: domainObject.id,
      action: "updated",
      version: index,
      changedFields: ["name"],
      attributeTypeKeys: [],
      occurredAt: `2026-09-0${1 + (index % 8)}T10:00:00Z`,
      actor: null,
    });
    vi.mocked(api.objectHistory)
      .mockResolvedValueOnce({ items: Array.from({ length: 10 }, (_, index) => entry(index)), nextCursor: "older" })
      .mockResolvedValueOnce({ items: Array.from({ length: 5 }, (_, index) => entry(index + 10)), nextCursor: null })
      .mockResolvedValueOnce({ items: [], nextCursor: null });
    render(<HistoryPanel objectTypeKey="domain" objectId={domainObject.id} />);
    expect(await screen.findByText("Showing 10 changes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load older history" }));
    expect(await screen.findByText("Showing 15 changes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show fewer" }));
    expect(screen.getByText("Showing 10 changes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "Relationships" }));
    await waitFor(() =>
      expect(api.objectHistory).toHaveBeenLastCalledWith("domain", domainObject.id, {
        pageSize: 10,
        kind: "relationships",
      }),
    );
    expect(await screen.findByText("No change matches.")).toBeInTheDocument();
  });

  it("reads through the page's client, so a new type's empty record in the preview asks the server nothing", async () => {
    // 0.10 T1: the preview's History panel asked the live API for the empty record's history (404).
    vi.mocked(api.objectHistory).mockClear();
    render(
      <PreviewDataProvider client={createPreviewClient(testModel, testModel)}>
        <HistoryPanel model={testModel} objectTypeKey="domain" objectId={PREVIEW_EMPTY_ID} />
      </PreviewDataProvider>,
    );
    expect(await screen.findByText("No history recorded yet.")).toBeInTheDocument();
    expect(api.objectHistory).not.toHaveBeenCalled();
  });
});
