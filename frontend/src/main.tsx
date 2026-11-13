import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { API_URL } from "@/api/address";
import { startSession } from "@/api/session";
import { ResetPasswordScreen, takeResetToken } from "@/features/sign-in/ResetPasswordScreen";
import { SignInScreen } from "@/features/sign-in/SignInScreen";
import { reloadOnStaleChunk } from "@/lib/reloadOnStaleChunk";
import { ErrorBoundary } from "@/ui/ErrorBoundary";
import "@fontsource-variable/instrument-sans/wght.css";
import "@fontsource-variable/jetbrains-mono/wght.css";
// The display typefaces of the Hearth and Studio themes and the text face of Instrument (0.17 UX1); a browser
// fetches a face only when a theme uses it.
import "@fontsource-variable/fraunces/opsz.css";
import "@fontsource-variable/bricolage-grotesque/opsz.css";
import "@fontsource-variable/inter/wght.css";
import "./styles.css";

// The application loads once a session exists: the sign-in screens do not carry it (0.17 RF3).
const App = lazy(() => import("@/app/App"));

// A tab left open across a deployment reloads once instead of failing on a chunk that is gone.
reloadOnStaleChunk();

const root = ReactDOM.createRoot(document.getElementById("root")!);

/** While the session starts (0.12 I2): the engine out of reach with a retry. */
function Starting({ unreachable }: { unreachable?: boolean }) {
  return (
    <main className="session-start" aria-busy={!unreachable}>
      {unreachable ? (
        <div role="alert">
          <h1>The engine cannot be reached</h1>
          <p>
            This application calls the engine at <code>{API_URL}</code>, which did not answer. Check that it is running,
            then try again.
          </p>
          <button type="button" className="primary" onClick={() => void start()}>
            Try again
          </button>
        </div>
      ) : (
        <p>Signing in…</p>
      )}
    </main>
  );
}

async function start() {
  if (window.location.pathname === "/reset-password") {
    // Asking for a new password, or choosing it with a link (0.12 I6): the person has no session.
    root.render(
      <React.StrictMode>
        <ResetPasswordScreen token={takeResetToken()} />
      </React.StrictMode>,
    );
    return;
  }
  root.render(<Starting />);
  try {
    if ((await startSession()) === "sign-in") {
      // The application's own screen (0.12 I5); the engine decides each step.
      root.render(
        <React.StrictMode>
          <SignInScreen />
        </React.StrictMode>,
      );
      return;
    }
  } catch {
    root.render(<Starting unreachable />);
    return;
  }
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <Suspense fallback={<Starting />}>
          <App />
        </Suspense>
      </ErrorBoundary>
    </React.StrictMode>,
  );
}

void start();
