import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { domainObject } from "../test/fixtures";
import { HistoryPanel } from "./HistoryPanel";

vi.mock("../api/client", () => ({ api: { objectHistory: vi.fn() } }));

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
    expect(await screen.findByText("Object updated")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load older history" }));
    expect(await screen.findByText("Attribute created")).toBeInTheDocument();
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
    expect(await screen.findByText("Object created")).toBeInTheDocument();
    expect(api.objectHistory).toHaveBeenLastCalledWith("domain", domainObject.id, { cursor: "older", pageSize: 20 });
  });
});
