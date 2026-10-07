import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { jobEventsUrl, jobOutputUrl } from "@/api/client";
import { testModel } from "@/test/fixtures";
import type { Job } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { JobNotificationsProvider, useJobNotifications } from "./JobNotifications";

/** An EventSource the test drives: what the engine would push over a job's stream. */
class FakeEventSource {
  static opened: FakeEventSource[] = [];
  listeners: ((event: MessageEvent<string>) => void)[] = [];
  closed = false;
  constructor(public url: string) {
    FakeEventSource.opened.push(this);
  }
  addEventListener(_type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.push(listener);
  }
  close() {
    this.closed = true;
  }
  push(job: Partial<Job>) {
    act(() => this.listeners.forEach((listener) => listener({ data: JSON.stringify(job) } as MessageEvent<string>)));
  }
}

const exportJob = (state: Job["state"], extra: Partial<Job> = {}): Job =>
  ({
    id: "j1",
    kind: "export",
    state,
    parameters: { scope: { types: [{ objectTypeKey: "domain" }] } },
    output: null,
    ...extra,
  }) as Job;

function Start({ job }: { job: Job }) {
  const { follow } = useJobNotifications();
  return <button onClick={() => follow(job)}>Start</button>;
}

function renderWith(job: Job, onNavigate = vi.fn()) {
  render(
    <ToastProvider>
      <JobNotificationsProvider model={testModel} onNavigate={onNavigate}>
        <Start job={job} />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
  return onNavigate;
}

describe("JobNotifications (0.9 J1u)", () => {
  beforeEach(() => {
    FakeEventSource.opened = [];
    window.sessionStorage.clear();
    vi.stubGlobal("EventSource", FakeEventSource);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("says an export started, follows its stream and says it completed with Download and View job", () => {
    const onNavigate = renderWith(exportJob("queued"));
    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(screen.getByRole("status")).toHaveTextContent("Export of Domains started.");
    const [stream] = FakeEventSource.opened;
    expect(stream.url).toBe(jobEventsUrl("j1"));
    expect(JSON.parse(window.sessionStorage.getItem("rdm.followedJobs")!)).toEqual(["j1"]);

    stream.push(exportJob("running"));
    stream.push(exportJob("completed", { output: { bytes: 10 } as Job["output"] }));
    expect(stream.closed).toBe(true);
    expect(screen.getByRole("status")).toHaveTextContent("Export of Domains completed.");
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute("href", jobOutputUrl("j1"));
    fireEvent.click(screen.getAllByRole("link", { name: "View job" }).at(-1)!);
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "jobs", jobId: "j1" });
    expect(JSON.parse(window.sessionStorage.getItem("rdm.followedJobs")!)).toEqual([]);
  });

  it("says a failed export failed, linking only to its page", () => {
    renderWith(exportJob("queued"));
    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    FakeEventSource.opened[0].push(exportJob("failed"));
    expect(screen.getByRole("status")).toHaveTextContent("Export of Domains failed.");
    expect(screen.queryByRole("link", { name: "Download" })).not.toBeInTheDocument();
  });

  it("follows again after a reload the jobs this tab started", () => {
    window.sessionStorage.setItem("rdm.followedJobs", JSON.stringify(["j1"]));
    renderWith(exportJob("queued"));
    expect(FakeEventSource.opened.map((source) => source.url)).toEqual([jobEventsUrl("j1")]);
    FakeEventSource.opened[0].push(exportJob("cancelled"));
    expect(screen.getByRole("status")).toHaveTextContent("Export of Domains was cancelled.");
  });
});
