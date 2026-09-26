import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import { HistoryPanel } from "@/features/objects/panels/HistoryPanel";

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
          },
        ],
        nextCursor: null,
      });
    render(<HistoryPanel objectTypeKey="domain" objectId={domainObject.id} />);
    expect(await screen.findByText("Record updated")).toBeInTheDocument();
    expect(screen.getByText("Changed name")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load older history" }));
    expect(await screen.findByText("Field value added")).toBeInTheDocument();
    expect(screen.getByText("Changed code")).toBeInTheDocument();
    await waitFor(() =>
      expect(api.objectHistory).toHaveBeenLastCalledWith("domain", domainObject.id, { cursor: "older", pageSize: 20 }),
    );
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
        },
      ],
      nextCursor: null,
    });
    render(<HistoryPanel model={testModel} objectTypeKey="domain" objectId={domainObject.id} />);
    expect(await screen.findByText("Relationship created")).toBeInTheDocument();
    expect(screen.getByText("Record created")).toBeInTheDocument();
    expect(screen.getByText("Changed Code")).toBeInTheDocument();
    expect(screen.queryByText(/expectedChangeSetVersion|fromObjectId|initialRelations|objectTypeKey/)).toBeNull();
  });
});
