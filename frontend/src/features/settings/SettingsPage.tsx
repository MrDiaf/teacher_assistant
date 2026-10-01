import { useEffect, useState } from "react";

import { Icon } from "../../platform/ui";
import { AiAccountSettings } from "../ai/AiAccountSettings";
import { mailApi } from "../inbox/api";
import type { MailConnectionInput, MailConnectionStatus } from "../inbox/types";

const EMPTY: MailConnectionInput = {
  host: "",
  port: 993,
  tls_mode: "implicit_tls",
  mailbox: "INBOX",
  username: "",
  password: "",
};

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not yet";
}

export function SettingsPage() {
  const [status, setStatus] = useState<MailConnectionStatus | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    mailApi
      .status(controller.signal)
      .then((value) => {
        setStatus(value);
        if (value.host) {
          setForm((current) => ({
            ...current,
            host: value.host ?? "",
            port: value.port ?? 993,
            tls_mode: value.tls_mode ?? "implicit_tls",
            mailbox: value.mailbox ?? "INBOX",
            username: value.username ?? "",
            password: "",
          }));
        }
      })
      .catch((reason: Error) => setError(reason.message));
    return () => controller.abort();
  }, []);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "The request failed safely.",
      );
    } finally {
      setBusy(false);
    }
  }

  function update<K extends keyof MailConnectionInput>(
    key: K,
    value: MailConnectionInput[K],
  ) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <main className="settings-page" aria-labelledby="settings-title">
      <header className="module-heading">
        <div>
          <p className="eyebrow">Private integrations</p>
          <h1 id="settings-title">Settings</h1>
          <p>Connect one dedicated forwarding mailbox for your local Inbox.</p>
        </div>
      </header>

      <AiAccountSettings />

      <section
        className="mail-settings-card"
        aria-labelledby="mail-settings-title"
      >
        <div className="mail-settings-intro">
          <span className="module-icon">
            <Icon name="inbox" />
          </span>
          <div>
            <p className="eyebrow">Inbound only</p>
            <h2 id="mail-settings-title">Mail inbox</h2>
            <p>
              Use a dedicated mailbox and forward only the school mail you want
              stored here. Teacher Assistant cannot create the mailbox or
              forwarding rule.
            </p>
          </div>
          <span className={`connection-pill ${status?.status ?? "none"}`}>
            {status?.connected
              ? "Connected"
              : status?.status === "error"
                ? "Needs attention"
                : status?.status === "reconnect_required"
                  ? "Reconnect required"
                  : "Not connected"}
          </span>
        </div>

        {status?.safe_error && (
          <p className="inline-alert" role="status">
            {status.safe_error}
          </p>
        )}
        {status?.source_warning && (
          <p className="inline-warning" role="status">
            {status.source_warning}
          </p>
        )}
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="inline-success" role="status">
            {notice}
          </p>
        )}

        {status?.host && (
          <dl className="mail-health">
            <div>
              <dt>Last checked</dt>
              <dd>{formatTime(status.last_checked_at)}</dd>
            </div>
            <div>
              <dt>Next check</dt>
              <dd>{formatTime(status.next_check_at)}</dd>
            </div>
            <div>
              <dt>Skipped safely</dt>
              <dd>{status.quarantined_count}</dd>
            </div>
          </dl>
        )}

        <form
          className="mail-connect-form"
          onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              const next = await mailApi.connect(form);
              setStatus(next);
              setForm((current) => ({ ...current, password: "" }));
              setNotice(
                "The dedicated mailbox was tested and connected over verified TLS.",
              );
            });
          }}
        >
          <label>
            IMAP host
            <input
              autoComplete="off"
              required
              value={form.host}
              onChange={(event) => update("host", event.target.value)}
              placeholder="imap.example.com"
            />
          </label>
          <label>
            Port
            <input
              min="1"
              max="65535"
              required
              type="number"
              value={form.port}
              onChange={(event) => update("port", Number(event.target.value))}
            />
          </label>
          <label>
            TLS mode
            <select
              value={form.tls_mode}
              onChange={(event) =>
                update(
                  "tls_mode",
                  event.target.value as MailConnectionInput["tls_mode"],
                )
              }
            >
              <option value="implicit_tls">Implicit TLS</option>
              <option value="starttls">STARTTLS</option>
            </select>
          </label>
          <label>
            Mailbox
            <input
              required
              value={form.mailbox}
              onChange={(event) => update("mailbox", event.target.value)}
            />
          </label>
          <label>
            Username
            <input
              autoComplete="username"
              required
              value={form.username}
              onChange={(event) => update("username", event.target.value)}
            />
          </label>
          <label>
            App password
            <input
              autoComplete="new-password"
              required
              type="password"
              value={form.password}
              onChange={(event) => update("password", event.target.value)}
            />
            <small>
              Sent once to the backend and never returned to this page.
            </small>
          </label>
          <div className="mail-settings-actions">
            <button className="primary-button" disabled={busy} type="submit">
              {status?.host ? "Reconnect mailbox" : "Connect mailbox"}
            </button>
            <button
              disabled={busy || !status?.connected}
              type="button"
              onClick={() =>
                void run(async () => {
                  const next = await mailApi.test();
                  setStatus(next);
                  setNotice("Connection test passed.");
                })
              }
            >
              Test connection
            </button>
            <button
              disabled={busy || !status?.connected}
              type="button"
              onClick={() =>
                void run(async () => {
                  const result = await mailApi.check();
                  setStatus(result.status);
                  setNotice(
                    `Check complete: ${result.imported_count} imported, ${result.quarantined_count} skipped safely.`,
                  );
                })
              }
            >
              Check mail
            </button>
            <button
              className="danger-button"
              disabled={busy || !status?.host}
              type="button"
              onClick={() =>
                void run(async () => {
                  if (
                    !window.confirm(
                      "Disconnect this mailbox? Imported Inbox mail will remain.",
                    )
                  )
                    return;
                  await mailApi.disconnect();
                  setStatus(await mailApi.status());
                  setNotice(
                    "Mailbox disconnected. Imported mail remains available.",
                  );
                })
              }
            >
              Disconnect
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
