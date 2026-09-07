import { useCallback, useEffect, useState } from "react";

import { Icon } from "../../components/Icon";
import { mailApi } from "./api";
import type { MailListItem, MailMessage } from "./types";

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Date unavailable";
}

function MailDetail({
  message,
  busy,
  onArchive,
  onDelete,
  onToggleRead,
}: {
  message: MailMessage;
  busy: boolean;
  onArchive: () => void;
  onDelete: () => void;
  onToggleRead: () => void;
}) {
  const to = message.addresses.filter((item) => item.kind === "to");
  const replyTo = message.addresses.filter((item) => item.kind === "reply_to");
  return (
    <article className="mail-detail" aria-labelledby="mail-detail-subject">
      <header>
        <div>
          <p className="mail-source-label">
            <Icon name="inbox" size={15} /> Mail · forwarded content unverified
          </p>
          <h2 id="mail-detail-subject">{message.subject}</h2>
          <p>
            <strong>{message.sender_name ?? message.sender_address}</strong>{" "}
            &lt;{message.sender_address}&gt;
          </p>
          <p>
            To{" "}
            {to.map((item) => item.address).join(", ") ||
              "recipient unavailable"}
          </p>
          {replyTo.length > 0 && (
            <p>Reply-To {replyTo.map((item) => item.address).join(", ")}</p>
          )}
          <time dateTime={message.source_date ?? message.ingested_at}>
            {formatTime(message.source_date ?? message.ingested_at)}
          </time>
        </div>
        <div className="mail-detail-actions">
          <button disabled={busy} onClick={onToggleRead} type="button">
            Mark {message.is_read ? "unread" : "read"}
          </button>
          <button disabled={busy} onClick={onArchive} type="button">
            {message.is_archived ? "Move to Inbox" : "Archive"}
          </button>
          <button
            className="danger-button"
            disabled={busy}
            onClick={onDelete}
            type="button"
          >
            <Icon name="trash" size={15} /> Delete locally
          </button>
        </div>
      </header>

      {message.body_html && (
        <p className="mail-html-notice">
          HTML mail converted to safe passive text. Remote images are blocked.
        </p>
      )}
      <pre className="mail-body">
        {message.body_text || "This message has no readable body."}
      </pre>

      {message.attachments.length > 0 && (
        <section
          className="mail-attachments"
          aria-labelledby="mail-attachments-title"
        >
          <h3 id="mail-attachments-title">Attachments</h3>
          <ul>
            {message.attachments.map((attachment) => (
              <li key={attachment.id}>
                <Icon name="file" size={17} />
                <span>
                  <strong>{attachment.original_filename}</strong>
                  <small>
                    {attachment.mime_type} ·{" "}
                    {attachment.file_size.toLocaleString()} bytes
                  </small>
                </span>
                {attachment.status === "stored" ? (
                  <a href={mailApi.attachmentUrl(attachment.id)}>Download</a>
                ) : (
                  <span className="omitted-attachment">
                    Omitted —{" "}
                    {attachment.omission_reason ?? "unsafe attachment"}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}

export function InboxPage() {
  const [messages, setMessages] = useState<MailListItem[]>([]);
  const [selected, setSelected] = useState<MailMessage | null>(null);
  const [search, setSearch] = useState("");
  const [archived, setArchived] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const result = await mailApi.list(
          { search, archived, unreadOnly },
          signal,
        );
        setMessages(result);
        if (selected && !result.some((item) => item.id === selected.id))
          setSelected(null);
      } catch (reason) {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Inbox could not be loaded.",
          );
        }
      } finally {
        setLoading(false);
      }
    },
    [archived, search, selected, unreadOnly],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [load]);

  async function openMessage(item: MailListItem) {
    setBusy(true);
    setError(null);
    try {
      let message = await mailApi.get(item.id);
      if (!message.is_read)
        message = await mailApi.update(item.id, { is_read: true });
      setSelected(message);
      setMessages((current) =>
        current.map((entry) =>
          entry.id === item.id ? { ...entry, is_read: true } : entry,
        ),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Message could not be opened.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function updateSelected(changes: {
    is_read?: boolean;
    is_archived?: boolean;
  }) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await mailApi.update(selected.id, changes);
      setSelected(updated);
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Message state could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function deleteSelected() {
    if (
      !selected ||
      !window.confirm(
        `Permanently delete “${selected.subject}” and its local attachments? The remote mailbox will not change.`,
      )
    )
      return;
    setBusy(true);
    setError(null);
    try {
      await mailApi.delete(selected.id);
      setSelected(null);
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The message could not be deleted safely.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="inbox-page" aria-labelledby="inbox-title">
      <header className="module-heading">
        <div>
          <p className="eyebrow">Forwarded mail</p>
          <h1 id="inbox-title">Inbox</h1>
          <p>Private local copies from your dedicated read-only mailbox.</p>
        </div>
        <button
          className="quiet-button"
          disabled={loading}
          onClick={() => void load()}
          type="button"
        >
          <Icon name="refresh" size={17} /> Refresh list
        </button>
      </header>

      <div className="inbox-toolbar">
        <label className="inbox-search">
          Search mail
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Sender, subject, or message text"
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(event) => setUnreadOnly(event.target.checked)}
          />{" "}
          Unread only
        </label>
        <div className="inbox-view-toggle" aria-label="Mailbox view">
          <button
            aria-pressed={!archived}
            onClick={() => setArchived(false)}
            type="button"
          >
            Inbox
          </button>
          <button
            aria-pressed={archived}
            onClick={() => setArchived(true)}
            type="button"
          >
            Archive
          </button>
        </div>
      </div>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}

      <div className="inbox-layout">
        <section
          className="mail-list"
          aria-label={archived ? "Archived mail" : "Inbox mail"}
        >
          {loading ? (
            <p className="inbox-empty">Loading mail…</p>
          ) : messages.length === 0 ? (
            <p className="inbox-empty">
              {search
                ? "No mail matches this search."
                : archived
                  ? "No archived mail."
                  : "No forwarded mail yet. Connect a dedicated mailbox in Settings, then check mail."}
            </p>
          ) : (
            <ul>
              {messages.map((item) => (
                <li key={item.id}>
                  <button
                    className={`${selected?.id === item.id ? "selected " : ""}${item.is_read ? "read" : "unread"}`}
                    onClick={() => void openMessage(item)}
                    type="button"
                  >
                    <span className="mail-list-top">
                      <strong>{item.sender_name ?? item.sender_address}</strong>
                      <time dateTime={item.source_date ?? item.ingested_at}>
                        {formatTime(item.source_date ?? item.ingested_at)}
                      </time>
                    </span>
                    <span className="mail-list-subject">{item.subject}</span>
                    <span className="mail-list-meta">
                      <span className="mail-source-label">Mail</span>
                      {item.attachment_count > 0 && (
                        <span>
                          {item.attachment_count} attachment
                          {item.attachment_count === 1 ? "" : "s"}
                        </span>
                      )}
                      {item.omitted_attachment_count > 0 && (
                        <span>{item.omitted_attachment_count} omitted</span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        {selected ? (
          <MailDetail
            busy={busy}
            message={selected}
            onArchive={() =>
              void updateSelected({ is_archived: !selected.is_archived })
            }
            onDelete={() => void deleteSelected()}
            onToggleRead={() =>
              void updateSelected({ is_read: !selected.is_read })
            }
          />
        ) : (
          <section className="mail-detail-empty">
            <Icon name="inbox" size={34} />
            <h2>Select a message</h2>
            <p>
              Forwarded content is unverified and never sent to the Assistant
              automatically.
            </p>
          </section>
        )}
      </div>
    </main>
  );
}
