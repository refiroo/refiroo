import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { ObjectTable } from "@/ui/ObjectTable";
import { staticWindow } from "@/test/cursorWindow";

describe("ObjectTable", () => {
  it("renders model-derived column headers and values for one object type", () => {
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "code"]}
        list={staticWindow([domainObject])}
        pageSize={20}
        onOpen={() => {}}
      />,
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Code")).toBeInTheDocument();
    expect(screen.getByText("Connections")).toBeInTheDocument();
    expect(screen.getByText("CONNECTIONS")).toBeInTheDocument();
  });

  it("renders the same generic columns for a different object type", () => {
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "objectType"]}
        list={staticWindow([codelistObject])}
        pageSize={20}
        onOpen={() => {}}
      />,
    );
    expect(screen.getByText("Timetable types")).toBeInTheDocument();
    expect(screen.getByText("Codelist")).toBeInTheDocument();
  });

  it("resizes configured data columns by keyboard without resizing the actions column", () => {
    const onColumnWidth = vi.fn();
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "code"]}
        list={staticWindow([domainObject])}
        pageSize={20}
        onOpen={() => {}}
        onColumnWidth={onColumnWidth}
        renderActions={() => <button>Actions</button>}
      />,
    );
    fireEvent.keyDown(screen.getByRole("separator", { name: "Resize Name column" }), { key: "ArrowRight" });
    expect(onColumnWidth).toHaveBeenCalledWith("name", 190);
    expect(screen.getAllByRole("separator")).toHaveLength(2);
  });
});
