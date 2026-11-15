import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Job } from "@/types";
import { JobProduced, producedBy } from "./JobProduced";

const held = vi.hoisted(() => ({ groups: [] as string[] }));
vi.mock("@/state/useMe", () => ({ useHoldsGroup: (key: string) => held.groups.includes(key) }));

const job = (kind: Job["kind"], parameters: Record<string, unknown>): Job => ({ id: "j", kind, parameters }) as Job;

describe("JobProduced", () => {
  it("leads a job to what it produced, where the caller can open it", () => {
    held.groups = ["copy-move"];
    render(
      <JobProduced
        job={job("mappingInference", { mappingKey: "map", sourceWorkspaceKey: "a", targetWorkspaceKey: "b" })}
      />,
    );
    expect(screen.getByRole("link", { name: "Open the mapping" })).toBeInTheDocument();
  });

  it("offers nothing the caller cannot open", () => {
    held.groups = [];
    const { container } = render(<JobProduced job={job("inference", { draftId: "d1" })} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("names an assistant task's page to everyone, and says nothing for a job with nothing to open", () => {
    held.groups = [];
    expect(producedBy(job("aiTask", { taskId: "t1" }))?.route).toEqual({
      kind: "settings",
      page: "ai-tasks",
      taskId: "t1",
    });
    expect(producedBy(job("profile", { sourceFileId: "s" }))).toBeUndefined();
  });
});
