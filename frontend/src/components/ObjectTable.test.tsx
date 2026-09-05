import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { codelistObject, domainObject, testModel } from "../test/fixtures";
import { ObjectTable } from "./ObjectTable";

describe("ObjectTable", () => {
  it("renders model-derived column headers and values for one object type", () => {
    render(<ObjectTable model={testModel} columns={["name", "code"]} objects={[domainObject]} onOpen={() => {}} />);
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Code")).toBeInTheDocument();
    expect(screen.getByText("Connections")).toBeInTheDocument();
    expect(screen.getByText("CONNECTIONS")).toBeInTheDocument();
  });

  it("renders the same generic columns for a different object type", () => {
    render(
      <ObjectTable model={testModel} columns={["name", "objectType"]} objects={[codelistObject]} onOpen={() => {}} />,
    );
    expect(screen.getByText("Timetable types")).toBeInTheDocument();
    expect(screen.getByText("Codelist")).toBeInTheDocument();
  });
});
