import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { DesignCheckView } from "./DesignCheckView";
import { designCheck, designTask } from "./designFixture";

const show = (canRelease: boolean, onLoad = vi.fn()) =>
  render(
    <DesignCheckView
      task={designTask()}
      check={designCheck}
      workspaceLabel="West"
      pending={false}
      canLoad
      canRelease={canRelease}
      onLoad={onLoad}
    />,
  );

vi.mock("@/api/aiClient", () => ({ ai: { taskChanges: vi.fn() } }));

describe("DesignCheckView", () => {
  it("shows a sheet's changed records behind a button, read by the sheet's source", async () => {
    vi.mocked(ai.taskChanges).mockResolvedValue({
      items: [
        {
          recordId: "r1",
          name: "Lab",
          table: "Durations",
          fields: [{ field: "minutes", label: "Minutes", now: 10, after: 15 }],
        },
      ],
      nextCursor: null,
    });
    const check = {
      ...designCheck,
      sheets: [
        {
          source: 2,
          sheet: "Durations",
          objectTypeKey: "duration",
          structure: false,
          rows: 1,
          created: 0,
          updated: 1,
          unchanged: 0,
          refused: 0,
        },
      ],
    };
    render(
      <DesignCheckView
        task={designTask()}
        check={check}
        workspaceLabel="West"
        pending={false}
        canLoad
        canRelease
        onLoad={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Show the 1 changed record of Durations" }));
    const changes = await screen.findByRole("group", { name: "Changed records of Durations" });
    expect(within(changes).getByText("Lab")).toBeInTheDocument();
    expect(ai.taskChanges).toHaveBeenCalledWith("task-1", { source: 2 }, undefined);
  });

  it("counts every row, folds the structure sheets and lists the refusals", () => {
    show(true);
    expect(screen.getByText(/165 rows checked: 123 created, 40 changed, 0 unchanged, 2 refused/)).toBeInTheDocument();
    const table = screen.getByRole("group", { name: "Check per sheet" });
    expect(within(table).getByText("Records the structure needs")).toBeInTheDocument();
    expect(within(table).queryByText("Structure Topic")).not.toBeInTheDocument();
    expect(screen.getByText(/Row 14: No category named Walk-in/)).toBeInTheDocument();
    expect(screen.getByText(/Installs the model change and activates it in West/)).toBeInTheDocument();
  });

  it("activates the model and loads, saving the import", () => {
    const onLoad = vi.fn();
    show(true, onLoad);
    fireEvent.click(screen.getByRole("button", { name: "Activate the model and load" }));
    expect(onLoad).toHaveBeenCalledWith({
      changeSetName: "Load of scheduling",
      saveProfile: { key: "scheduling", name: "scheduling" },
    });
  });

  it("hides the button without model-release and says who runs the load", () => {
    show(false);
    expect(screen.queryByRole("button", { name: /load/i })).not.toBeInTheDocument();
    expect(screen.getByText(/a model administrator runs this load/)).toBeInTheDocument();
  });

  it("counts the relationships in the figures and lists saving the import in the order", () => {
    show(true);
    expect(screen.getByText(/2 refused, 3 relationships\./)).toBeInTheDocument();
    expect(screen.getByText(/Saves the import/)).toBeInTheDocument();
  });
});
