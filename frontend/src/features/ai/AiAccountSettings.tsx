import { useEffect, useState } from "react";

import { Icon } from "../../platform/ui";
import { aiApi } from "./api";
import type { AiAuthStatus, AiDeviceLogin } from "./types";

export function AiAccountSettings() {
  const [status, setStatus] = useState<AiAuthStatus | null>(null);
  const [attempt, setAttempt] = useState<AiDeviceLogin | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    aiApi
      .getAuthStatus(controller.signal)
      .then(setStatus)
      .catch((reason: Error) => {
        if (reason.name !== "AbortError") setError(reason.message);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!attempt || attempt.status !== "pending") return;
    const controller = new AbortController();
    let timer = 0;

    async function poll() {
      try {
        const latest = await aiApi.getDeviceLogin(
          attempt!.login_id,
          controller.signal,
        );
        setAttempt(latest);
        if (latest.status === "completed") {
          const connected = await aiApi.getAuthStatus(controller.signal);
          setStatus(connected);
          if (connected.authenticated) setAttempt(null);
          return;
        }
        if (latest.status === "pending") {
          timer = window.setTimeout(() => void poll(), 1200);
        }
      } catch (reason) {
        if ((reason as Error).name !== "AbortError") {
          setError(
            reason instanceof Error
              ? reason.message
              : "ChatGPT sign-in status could not be checked.",
          );
        }
      }
    }

    timer = window.setTimeout(() => void poll(), 900);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [attempt?.login_id, attempt?.status]);

  async function startLogin() {
    setBusy(true);
    setError(null);
    try {
      setAttempt(await aiApi.startDeviceLogin());
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "ChatGPT sign-in could not be started.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    setError(null);
    try {
      setStatus(await aiApi.logout());
      setAttempt(null);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "ChatGPT sign-out could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="ai-settings-card" aria-labelledby="ai-settings-title">
      <div className="ai-settings-intro">
        <span className="module-icon">
          <Icon name="assistant" />
        </span>
        <div>
          <p className="eyebrow">Shared private AI</p>
          <h2 id="ai-settings-title">ChatGPT connection</h2>
          <p>
            One private connection powers Assistant, note summaries, prettify,
            and sanitized error explanations.
          </p>
        </div>
        <span
          className={`connection-pill ${status?.authenticated ? "connected" : "none"}`}
        >
          {status?.authenticated ? "Connected" : "Not connected"}
        </span>
      </div>

      {status?.authenticated && (
        <p className="ai-account-summary">
          Connected with{" "}
          {status.email ?? status.plan_type?.replaceAll("_", " ") ?? "ChatGPT"}.
        </p>
      )}
      {attempt?.status === "pending" && (
        <div className="ai-device-login" role="status">
          <a href={attempt.verification_url} rel="noreferrer" target="_blank">
            Open ChatGPT sign-in
          </a>
          <span>
            Enter code <code>{attempt.user_code}</code>
          </span>
        </div>
      )}
      {attempt?.status === "failed" && (
        <p className="inline-error" role="alert">
          {attempt.safe_error ?? "This sign-in attempt failed safely."}
        </p>
      )}
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}

      <div className="ai-settings-actions">
        {status?.authenticated ? (
          <button disabled={busy} onClick={() => void logout()} type="button">
            Sign out
          </button>
        ) : (
          <button
            className="primary-button"
            disabled={busy || attempt?.status === "pending"}
            onClick={() => void startLogin()}
            type="button"
          >
            {busy ? "Starting sign-in…" : "Sign in with ChatGPT"}
          </button>
        )}
      </div>
    </section>
  );
}
