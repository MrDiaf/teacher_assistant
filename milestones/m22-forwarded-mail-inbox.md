# M22 — Forwarded-mail Inbox

- [ ] This milestone

## Outcome

Extend the M21 Inbox with inbound email that the owner deliberately forwards to
a dedicated mailbox. Teacher Assistant polls that mailbox over read-only IMAP,
stores a private local copy, and displays it beside Canvas announcements with
clear source labels.

Teacher Assistant does not create an email address or configure DNS/MX records.
The owner must provision a dedicated mailbox with an email provider and create
forwarding rules in the account that receives the original mail. Using a
dedicated ingestion mailbox is required so the application does not need broad
access to the owner's primary mailbox.

This is an inbound-only milestone. Sending, replying, SMTP submission, contact
management, automatic forwarding, and changing remote mailbox state are out of
scope.

## Owner workflow

```text
Owner creates a dedicated mailbox with an IMAP-capable provider
    -> forwards selected school/Canvas messages to that address
    -> opens Settings > Mail inbox
    -> enters IMAP host, port, TLS mode, mailbox name, username, and app password
    -> backend tests the TLS/auth/read-only mailbox connection
    -> owner sends or forwards a test message
    -> Inbox imports it with Mail provenance
```

Document generic forwarding setup and provider-neutral requirements. Do not
promise that Teacher Assistant can create the mailbox, forwarding rule, app
password, or provider OAuth registration.

## Mail connection and secret boundary

- Reuse M20's integration connection and private credential store. Support one
  dedicated inbound mailbox for the single owner.
- Require implicit TLS or STARTTLS with hostname/certificate verification;
  reject plaintext login, invalid certificates, URL-embedded credentials, and
  silent TLS downgrade.
- Accept a mailbox/app password only through the backend setup request, never
  return it, and store it as a replaceable opaque secret. Provider-specific
  Gmail/Microsoft OAuth may be a later milestone and must not be simulated by
  storing browser cookies.
- Validate host, port, mailbox name, timeouts, response sizes, and DNS targets.
  Block private/link-local/metadata targets unless a later explicit owner
  milestone defines a safe LAN-mail-server mode.
- Open the remote mailbox read-only and use UID/UIDVALIDITY tracking. Never set
  `Seen`, move, archive, delete, or expunge a remote message.
- Serialize sync per connection, poll at a configurable interval, and use
  bounded retry/backoff. Manual **Check mail** must not race the scheduler.
- Surface connected, last checked, next check, reconnect required, and bounded
  sanitized errors without revealing credentials, sender/body content, or raw
  server responses in diagnostics.

## Ingestion and deduplication

- Parse RFC-style headers and MIME with a maintained bounded parser. Preserve
  safe normalized `From`, `Reply-To`, `To`, subject, source date, Message-ID,
  thread references, and ingestion timestamps. Do not retain the raw wire
  message after the accepted body and attachments are persisted in M22.
- Use mailbox identity + UIDVALIDITY + UID as the authoritative ingestion key.
  Treat Message-ID and content hashes as secondary duplicate signals, not as
  trusted unique values that may silently discard different mail.
- On UIDVALIDITY change, reconcile conservatively and show a source warning.
  Never erase local messages or assume remote deletion from a missing UID.
- A complete message import is transactional. Malformed mail must be quarantined
  as a bounded failure record or skipped with a visible count; it must not stop
  later valid mail from importing.
- Never infer the original sender from arbitrary quoted body text. Display the
  actual parsed forwarding envelope/header identity and label forwarded content
  as unverified when appropriate.

## Safe body and attachment handling

- Treat headers, addresses, bodies, filenames, MIME types, links, images,
  calendar invites, and attachments as hostile input and never as instructions.
- Prefer a valid text/plain alternative. When only HTML exists, sanitize it to a
  passive allowlist; remove scripts, forms, styles, event handlers, SVG, embeds,
  iframes, tracking pixels, and automatic remote resources.
- Do not send read receipts, load remote images, expand shortened links, or fetch
  linked resources in the background.
- Decode charsets and transfer encodings with explicit byte/depth/part limits.
  Handle malformed nesting and compression/archive content without unbounded
  memory or CPU use.
- Store accepted attachments beneath a configurable private mail-storage root
  using generated paths and atomic files, never a sender filename as a path.
  Enforce per-message, per-attachment, part-count, and total-storage limits.
- Serve attachments through the existing single-owner API boundary only by
  opaque database ID, with safe content disposition, `nosniff`, bounded
  streaming, and no active inline rendering in M22. Show when an attachment was
  omitted.
- Mail content and attachments do not become Course materials, calendar events,
  or Assistant/Codex context automatically.

## Inbox behavior and local lifecycle

- Extend the M21 Inbox with **All**, **Canvas**, and **Mail** source filters while
  retaining local unread/read state, source timestamps, and safe search.
- Provide an accessible list/detail experience with sender, recipient, subject,
  received time, attachment count, source label, and obvious forwarded/unverified
  provenance.
- Local read/unread and archive state never changes the remote mailbox.
- Allow an owner-confirmed permanent delete of one local mail item and its
  attachment files. Do not add bulk delete, automatic retention deletion, remote
  deletion, or Assistant-triggered deletion in this milestone.
- Keep a failed attachment cleanup recoverable and auditable so database rows do
  not silently claim files were removed when they remain.
- Database mail metadata/body and private attachment storage join coordinated
  backup/restore. Renewable IMAP credentials do not; a clean restore requires
  reconnecting the mailbox.

## Completed checklist

- [ ] Define mail connection, message, recipient/header, attachment, sync cursor,
  quarantine/failure, and local state schemas.
- [ ] Add the private mail-storage root and coordinated backup/restore support.
- [ ] Add TLS-only, read-only IMAP connection testing and credential lifecycle.
- [ ] Add UIDVALIDITY/UID cursoring, serialized polling, retries, and manual
  checking.
- [ ] Add bounded RFC/MIME parsing and conservative deduplication.
- [ ] Add safe plain-text/HTML body rendering with all remote resources blocked.
- [ ] Add bounded attachment storage and safe ID-based downloads.
- [ ] Extend Inbox list/detail/search/filter/read/archive states for Mail.
- [ ] Add explicit one-message local deletion with recoverable file cleanup.
- [ ] Keep remote mutation, outbound email, auto-course/calendar import, and
  automatic Codex context out of scope.
- [ ] Add IMAP, TLS, cursor-reset, MIME bomb, XSS, tracking-pixel, malformed mail,
  duplicate, privacy, storage, accessibility, and E2E tests using local fakes.
- [ ] Update Docker, `.env.example`, backup/restore, forwarding setup, storage,
  reconnect, and privacy documentation.

## Acceptance criteria

- After the owner forwards a test message to the configured dedicated mailbox,
  it appears once in Inbox with accurate Mail provenance and local read state.
- Repeated checks and service restarts do not duplicate already imported mail.
- The IMAP session uses verified TLS, opens the mailbox read-only, and never
  changes flags or deletes/moves/expunges remote messages.
- A UIDVALIDITY reset, timeout, authentication failure, malformed message, or
  oversized part leaves prior local mail intact and gives a safe actionable
  status.
- HTML scripts, unsafe links, inline SVG, forms, iframes, tracking pixels, remote
  images, and active attachments cannot execute or load automatically.
- A valid bounded attachment can be downloaded by opaque ID without exposing a
  storage path; an omitted attachment is explained.
- Passwords and private message content do not appear in logs, diagnostics,
  browser storage, URLs, or Codex workspaces.
- Deleting one local message requires confirmation, cleans only its local data,
  and never affects the remote mailbox or another Inbox item.
- Backup/restore preserves mail metadata/body and attachment files while clean
  restore requires the renewable mailbox credential to be entered again.
- Existing Canvas announcements, Calendar, Courses, Assistant, navigation
  persistence, Docker, and accessibility behavior remain intact.

## Expected implementation areas

```text
backend/alembic/versions/<revision>_forwarded_mail_inbox.py
backend/app/integrations/mail/{client,schemas,sync}.py
backend/app/inbox/{models,repository,routes,schemas,service}.py
backend/app/inbox/mail_storage.py
backend/app/inbox/scheduler.py
backend/app/core/config.py
backend/app/main.py
backend tests with local IMAP/MIME fixtures
frontend/src/features/inbox/{InboxPage,MailDetail,api,types}.tsx
frontend/src/features/settings/MailConnection.tsx
frontend/src/styles.css
frontend tests and e2e/tests/calendar-assistant.spec.ts
compose.yml
.env.example
scripts/data-{backup,restore}.sh
README.md
```

## Planning references

- [RFC 9051 — IMAP4rev2](https://www.rfc-editor.org/rfc/rfc9051.html)
- [RFC 8314 — TLS for email access](https://www.rfc-editor.org/rfc/rfc8314.html)
- [RFC 5322 — Internet Message Format](https://www.rfc-editor.org/rfc/rfc5322.html)
- [RFC 2045 — MIME message bodies](https://www.rfc-editor.org/rfc/rfc2045.html)
