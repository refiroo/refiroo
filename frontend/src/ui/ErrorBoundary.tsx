/**
 * What a page shows when one of its parts fails while rendering: what failed, that nothing was
 * saved by the failure, and a reload, instead of an empty page (reported 2026-10-14: a dialog's
 * error blanked the whole app with nothing in the server's logs). The details go to the browser's
 * console. A change of `resetKey` (the address) clears it, so navigating away recovers.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";
import { Notice } from "@/ui/Notice";

export class ErrorBoundary extends Component<
  { children: ReactNode; resetKey?: string },
  { error?: Error; key?: string }
> {
  state: { error?: Error; key?: string } = {};

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  static getDerivedStateFromProps(props: { resetKey?: string }, state: { error?: Error; key?: string }) {
    if (props.resetKey !== state.key) return { error: undefined, key: props.resetKey };
    return null;
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("This page stopped working:", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="error-boundary">
        <Notice
          tone="error"
          title="This page stopped working"
          actions={
            <button type="button" className="secondary" onClick={() => window.location.reload()}>
              Reload the page
            </button>
          }
        >
          A part of the page failed while showing: {error.message || String(error)}. Nothing was saved by the failure;
          what you saved before stays. Reload the page, or go elsewhere from the top bar. The details are in the
          browser's console.
        </Notice>
      </div>
    );
  }
}
