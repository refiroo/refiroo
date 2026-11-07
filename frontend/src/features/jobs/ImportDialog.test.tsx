import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { capabilitiesFixture } from "@/test/capabilities";
import { testModel } from "@/test/fixtures";
import type { ChangeSet, ImportProfile, Job } from "@/types";
import { ImportDialog, type ImportStart } from "./ImportDialog";
import { ImportFacts } from "./ImportOutcome";

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: {
    importProfiles: vi.fn(),
    startImport: vi.fn(),
    workspaces: vi.fn(),
    changeSets: vi.fn(),
    capabilities: vi.fn(),
  },
}));

const queued = { id: "j1", kind: "import", state: "queued" } as Job;

const profile = (key: string, extra: Partial<ImportProfile> = {}): ImportProfile => ({
  key,
  name: `Profile ${key}`,
  version: 1,
  checkedAgainst: "r1",
  modelKey: "m1",
  valid: true,
  problems: [],
  createdAt: "2026-10-01T00:00:00Z",
  updatedAt: "2026-10-01T00:00:00Z",
  sources: [
    {
      sheet: "Codes",
      applicationKey: "master",
      objectTypeKey: "domain",
      key: { attributeTypeKey: "code" },
      columns: [{ column: "Code", attributeTypeKey: "code" }],
    },
  ],
  valueMaps: {},
  ...extra,
});

const PROFILES = [
  profile("supplier"),
  profile("keyless", {
    sources: [{ sheet: "Codes", applicationKey: "master", objectTypeKey: "domain", columns: [{ column: "Code" }] }],
  }),
  profile("broken", { valid: false, problems: [{ path: "/sources/0", code: "UNKNOWN_OBJECT_TYPE", message: "…" }] }),
];

const file = new File(["Code,Name\nA,Alpha\n"], "codes.csv", { type: "text/csv" });

function open(start: ImportStart, onStarted = vi.fn()) {
  render(<ImportDialog model={testModel} start={start} onClose={vi.fn()} onStarted={onStarted} />);
  return onStarted;
}

async function chooseFileAndProfile(profileKey?: string) {
  fireEvent.change(screen.getByLabelText("File"), { target: { files: [file] } });
  const select = screen.getByLabelText("Profile");
  await waitFor(() => expect(select).not.toBeDisabled());
  if (profileKey) fireEvent.change(select, { target: { value: profileKey } });
}

const preview = () => fireEvent.click(screen.getByRole("button", { name: "Preview" }));

describe("ImportDialog (0.9 J4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.importProfiles).mockResolvedValue({ items: PROFILES, nextCursor: null });
    vi.mocked(api.startImport).mockResolvedValue(queued);
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture());
  });

  it("previews into the collection's live data, updating found records when a profile reads the file (D90, D92)", async () => {
    const onStarted = open({ context: { workspaceKey: "west" } });
    await chooseFileAndProfile("supplier");
    expect(screen.getByRole("radio", { name: "Update them" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Load the rows that can load" })).toBeChecked();
    preview();
    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(queued));
    expect(api.startImport).toHaveBeenCalledWith(
      file,
      {
        workspaceKey: "west",
        changeSetId: null,
        expectedChangeSetVersion: null,
        profileKey: "supplier",
        policy: "independent",
        onExisting: "overwrite",
        otherWorkspaceIds: "counterparts",
        stage: "preview",
      },
      expect.any(String),
    );
  });

  it("previews into the page's change set at its version, all or nothing, and keeps versions without a profile", async () => {
    open({ context: { workspaceKey: "west", changeSet: { id: "cs1", name: "Spring", version: 4 } } });
    await chooseFileAndProfile();
    expect(screen.getByRole("radio", { name: "Only if unchanged since the export" })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: "Load nothing unless every row loads" }));
    preview();
    await waitFor(() => expect(api.startImport).toHaveBeenCalled());
    expect(vi.mocked(api.startImport).mock.calls[0][1]).toEqual({
      workspaceKey: null,
      changeSetId: "cs1",
      expectedChangeSetVersion: 4,
      profileKey: null,
      policy: "atomic",
      onExisting: "reject",
      otherWorkspaceIds: "counterparts",
      stage: "preview",
    });
  });

  it("sends a retry of the same request with the same idempotency key, and a changed request with another", async () => {
    vi.mocked(api.startImport).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    open({ context: { workspaceKey: "west" } });
    await chooseFileAndProfile("supplier");
    preview();
    await screen.findByText("The import was not started");
    preview();
    await waitFor(() => expect(api.startImport).toHaveBeenCalledTimes(2));
    const [first, second] = vi.mocked(api.startImport).mock.calls;
    expect(second[2]).toBe(first[2]);
    fireEvent.click(screen.getByRole("radio", { name: "Refuse their rows" }));
    preview();
    await waitFor(() => expect(api.startImport).toHaveBeenCalledTimes(3));
    expect(vi.mocked(api.startImport).mock.calls[2][2]).not.toBe(first[2]);
  });

  it("loads another workspace's records as this workspace's own by default, or refuses them when chosen (0.9 J5, D99)", async () => {
    open({ context: { workspaceKey: "west" } });
    await chooseFileAndProfile();
    expect(screen.getByRole("radio", { name: "Load them as this workspace's own" })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: "Refuse them" }));
    preview();
    await waitFor(() => expect(api.startImport).toHaveBeenCalled());
    expect(vi.mocked(api.startImport).mock.calls[0][1]).toMatchObject({ otherWorkspaceIds: "refuse" });
  });

  it("lists a profile no longer valid without letting it be chosen, and warns of a profile without a key", async () => {
    open({ context: { workspaceKey: "west" } });
    await chooseFileAndProfile("keyless");
    expect(screen.getByRole("option", { name: /Profile broken \(no longer valid: 1 problem\)/ })).toBeDisabled();
    expect(screen.getByText("This profile has no key")).toBeInTheDocument();
    expect(screen.getByText(/sending the file twice creates its records twice/)).toBeInTheDocument();
  });

  it("shows a file over the limit at the file and a profile's problems at the profile", async () => {
    vi.mocked(api.startImport).mockRejectedValueOnce(
      new ApiError(413, "IMPORT_TOO_LARGE", "The file is larger than IMPORT_MAX_BYTES allows."),
    );
    open({ context: { workspaceKey: "west" } });
    await chooseFileAndProfile("supplier");
    preview();
    const fileInput = screen.getByLabelText("File");
    await waitFor(() => expect(fileInput).toHaveAttribute("aria-invalid", "true"));
    expect(fileInput.closest(".form-field")).toHaveTextContent("larger than IMPORT_MAX_BYTES");

    vi.mocked(api.startImport).mockRejectedValueOnce(
      new ApiError(422, "INVALID_IMPORT_PROFILE", "The profile is not valid.", {
        problems: [{ path: "/sources/0/columns/2", code: "UNKNOWN_ATTRIBUTE", message: "No attribute 'order'" }],
      }),
    );
    preview();
    const field = (await screen.findByText("The profile is not valid.")).closest(".form-field") as HTMLElement;
    expect(within(field).getByText("No attribute 'order' (/sources/0/columns/2)")).toBeInTheDocument();
    expect(screen.getByLabelText("Profile")).toHaveAttribute("aria-invalid", "true");
  });

  it("from Jobs, loads into a chosen workspace's change set at its version (D89)", async () => {
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [
        { key: "west", label: "West", status: "active", version: 1, createdAt: "", updatedAt: "" },
        { key: "east", label: "East", status: "active", version: 1, createdAt: "", updatedAt: "" },
      ],
      nextCursor: null,
    } as Awaited<ReturnType<typeof api.workspaces>>);
    vi.mocked(api.changeSets).mockImplementation(async (workspaceKey) => ({
      items:
        workspaceKey === "east" ? [{ id: "cs9", name: "Autumn", version: 7, workspaceKey: "east" } as ChangeSet] : [],
      nextCursor: null,
    }));
    open({});
    const workspace = screen.getByLabelText("Workspace");
    await waitFor(() => expect(workspace).not.toBeDisabled());
    fireEvent.change(workspace, { target: { value: "east" } });
    const into = screen.getByLabelText("Load into");
    // The change sets load after the workspace is chosen; on a loaded CI runner that takes longer than the default second.
    await screen.findByRole("option", { name: "Change set “Autumn”" }, { timeout: 5000 });
    // Choosing the workspace already chosen keeps the change sets read (found by test:browser:j4).
    fireEvent.change(workspace, { target: { value: "east" } });
    expect(screen.getByRole("option", { name: "Change set “Autumn”" })).toBeInTheDocument();
    expect(into).not.toBeDisabled();
    fireEvent.change(into, { target: { value: "cs9" } });
    await chooseFileAndProfile("supplier");
    preview();
    await waitFor(() => expect(api.startImport).toHaveBeenCalled());
    expect(vi.mocked(api.startImport).mock.calls[0][1]).toMatchObject({
      workspaceKey: null,
      changeSetId: "cs9",
      expectedChangeSetVersion: 7,
    });
  });

  it("says a workbook for people is read without a profile, and the job names the workbook (0.9 J6, D185)", async () => {
    open({ context: { workspaceKey: "west" } });
    await chooseFileAndProfile();
    expect(screen.getByText(/a workbook exported for people, read as it was written/)).toBeInTheDocument();
    render(
      <ImportFacts
        job={
          {
            ...queued,
            changeSetId: null,
            parameters: {
              file: { name: "values.xlsx", format: "xlsx", bytes: 2048 },
              profile: {
                key: null,
                version: null,
                embedded: { collection: "Values", exportedAt: "2026-10-10T09:00:00Z" },
                definition: { sources: [] },
              },
            },
          } as unknown as Job
        }
      />,
    );
    expect(screen.getByText(/^Read as exported from Values on /)).toHaveTextContent("2026");
  });
  it("offers no way to the AI assistant, and starts with a file carried from its dialog (0.16 AP6a)", () => {
    open({ context: { workspaceKey: "west" }, file });
    expect(screen.queryByRole("button", { name: /AI assistant/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview" })).toBeEnabled();
  });
});
