import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import { ObjectDetail } from "@/features/objects/ObjectDetail";

afterEach(() => vi.restoreAllMocks());

describe("ObjectDetail lifecycle controls", () => {
  it("does not expose object retirement controls or call a retirement API", async () => {
    vi.spyOn(api, "object").mockResolvedValue(domainObject);
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    render(
      <ObjectDetail
        model={testModel}
        application={testModel.applications[0]}
        objectTypeKey="domain"
        objectId={domainObject.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Connections" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retire object" })).not.toBeInTheDocument();
    expect(screen.queryByText(/retir/i)).not.toBeInTheDocument();
  });
});
