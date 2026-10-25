import React from "react";
import ReactDOM from "react-dom/client";
import App from "@/app/App";
import { API_URL } from "@/api/address";
import { startSession } from "@/api/session";
import { SignInScreen } from "@/features/sign-in/SignInScreen";
import { ErrorBoundary } from "@/ui/ErrorBoundary";
import "@fontsource-variable/instrument-sans/wght.css";
import "@fontsource-variable/jetbrains-mono/wght.css";
import "./styles.css";

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
        <App />
      </ErrorBoundary>
    </React.StrictMode>,
  );
}

void start();
