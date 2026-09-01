# M21 — Canvas announcement Inbox

- [ ] This milestone

## Outcome

Add an Inbox module and populate it with read-only Canvas course announcements.
Use the M20 Canvas API connection when available, while also supporting a
per-course Canvas Announcement RSS/Atom URL when institution-level OAuth or
personal API tokens are unavailable.

Canvas remains the authority. Imported announcements are a local read-only
mirror with source provenance; Teacher Assistant never posts, edits, replies to,
marks read in, or deletes anything in Canvas.

## Source paths

### Connected Canvas API

- Synchronize active Canvas courses through the current-user course endpoint.
- Retrieve announcements through `GET /api/v1/announcements` with explicit
  course context codes, date bounds, active-only behavior, and full pagination.
- Use only the read scopes established in M20.
- Make bounded sequential requests and honor Canvas rate limits and retry
  guidance.

### Per-course announcement feed

- Let the owner paste the RSS/Atom announcement URL exposed by a Canvas course.
- Treat the complete URL as a bearer secret: store it only in the M20 credential
  store and show a redacted origin/course label after setup.
- Require HTTPS, validate public DNS addresses, reject embedded URL credentials,
  disable environment proxies, and allow redirects only after revalidation and
  only within the exact configured Canvas origin.
- Feed-only setup links one source at a time and does not claim to be a full
  Canvas account connection.

M22 may later ingest Canvas notification emails forwarded by the owner. M21
must not parse a Canvas password, browser session, private HTML page, or copied
cookie as a fallback.

## Canvas course mapping

- Store a separate read-only catalog of remote Canvas course identifiers and
  safe display metadata. Do not change `CourseSourceType.MANUAL` or silently
  convert, overwrite, archive, or delete existing local courses.
- Let the owner explicitly map a remote Canvas course to at most one existing
  local course. A local course may map to at most one remote course for the
  single M20 connection.
- Unmapped Canvas courses and their announcements remain usable through Inbox
  with their Canvas names.
- Linking or unlinking changes only the relation. It never copies course files,
  assignments, grades, people, notes, calendars, or announcements into a local
  Course record and never deletes either side.

Automatic LMS course creation/import and assignment synchronization remain out
of scope.

## Synchronization and identity

- Use a conservative initial lookback window with a documented configurable
  default, then a high-water mark plus overlap so late edits are not missed.
- Identify an API item by connection, Canvas context code, and opaque Canvas
  announcement ID. Identify a feed item by feed source and stable entry ID, with
  a content fingerprint only as a guarded fallback.
- Upsert idempotently; repeated manual/background syncs must not create
  duplicates or reset local read state.
- Store source-created/source-updated times separately from local ingestion and
  last-seen times.
- Commit a source only after all required pages in that sync have been fetched
  and validated. A timeout, malformed page, permission error, or rate limit
  leaves the last known-good announcements intact.
- A complete authoritative API reconciliation may mark a previously mirrored
  announcement unavailable. A partial/failed API sync or feed sync must never
  infer deletion from absence.
- Run a configurable background sync with bounded exponential backoff and a
  manual **Sync now** action. Prevent overlapping syncs for the same source.

## Untrusted content and privacy

- Treat Canvas titles, author names, HTML bodies, links, attachment metadata,
  course names, errors, and feed fields as untrusted data.
- Parse into a bounded internal schema. Sanitize to a small passive HTML subset
  or render safe plain text; remove scripts, forms, styles, event handlers,
  embeds, iframes, tracking pixels, and automatic remote image/resource loads.
- Allow only safe link schemes. Open links with clear destination/provenance and
  appropriate opener isolation.
- Do not place Canvas credentials, feed URLs, raw upstream responses, or
  announcement bodies in logs or diagnostics.
- Do not provide Inbox or announcements to Codex automatically. Any future
  Assistant use requires a separate owner-defined bounded-context milestone.

## Inbox experience

- Add **Inbox** to the existing module-based navigation after Courses and update
  M19's versioned module validation without invalidating unrelated saved state.
- Provide an accessible announcement list/detail layout with unread/read local
  state, source/course filters, source timestamp, author when supplied, and a
  clear **Open in Canvas** link.
- Use local unread/read state only. Make it visually clear that it does not alter
  Canvas notification state.
- Show loading, empty, stale, partial-capability, disconnected, reconnect, and
  source-error states without hiding last known-good data.
- Provide source management in Settings and course mapping from Settings or the
  related local Course; do not overload the Calendar import dialog.
- Preserve the fixed sidebar, warm off-white background, green/gold palette,
  rounded cards, responsive behavior, keyboard focus, and reduced-motion rules.

## Completed checklist

- [ ] Add remote Canvas course, course mapping, announcement, source, and local
  read-state models/migrations.
- [ ] Add strict Canvas course/announcement/feed parsers and schemas.
- [ ] Add idempotent API and feed synchronization services with safe
  reconciliation.
- [ ] Add background scheduling, backoff, source locks, and manual sync.
- [ ] Add feed-secret handling and SSRF/redirect protections.
- [ ] Add explicit remote-to-local course linking and unlinking.
- [ ] Add Inbox navigation and accessible list/detail/filter states.
- [ ] Add safe passive rendering with remote resources blocked.
- [ ] Preserve provenance and open-in-Canvas behavior.
- [ ] Keep Canvas mutations, automatic local-course import, assignments, and
  automatic Codex context out of scope.
- [ ] Add parser, pagination, rate-limit, idempotency, reconciliation, XSS,
  prompt-injection, privacy, accessibility, and E2E tests.
- [ ] Update setup, source-method, sync, backup/restore, and privacy docs.

## Acceptance criteria

- A linked OAuth/manual-token connection shows announcements from every selected
  accessible Canvas course after a complete paginated sync.
- When API connection is unavailable, a valid per-course Canvas announcement
  feed can populate the same Inbox with explicit feed provenance.
- Repeated or overlapping sync attempts do not duplicate announcements or reset
  the owner's local read state.
- Edited announcements update safely; failed or partial syncs retain last
  known-good content.
- A remote Canvas course can be linked to an existing local course without
  creating, replacing, or deleting any Course record.
- Scripted HTML, unsafe URLs, embeds, event handlers, and remote tracking
  resources cannot execute or load in the Inbox.
- Read/unread changes are local and no request mutates Canvas.
- Secrets and full feed URLs never appear in browser responses, logs,
  diagnostics, or Codex workspaces.
- Disconnect/reconnect and unavailable-source states remain understandable and
  preserve locally mirrored announcements.
- Existing navigation persistence, Courses, Calendar, Assistant, Docker, and
  backup behavior remains intact.

## Expected implementation areas

```text
backend/alembic/versions/<revision>_canvas_announcements.py
backend/app/integrations/canvas/{client,schemas,sync}.py
backend/app/inbox/{models,repository,routes,schemas,service}.py
backend/app/inbox/scheduler.py
backend/app/main.py
backend tests with API/Atom fixtures and no live Canvas account
frontend/src/features/inbox/{InboxPage,AnnouncementDetail,api,types}.tsx
frontend/src/features/settings/CanvasConnection.tsx
frontend/src/features/courses/CoursesPage.tsx
frontend/src/components/AppShell.tsx
frontend/src/App.tsx
frontend/src/styles.css
frontend tests and e2e/tests/calendar-assistant.spec.ts
README.md
```

## Planning references

- [Canvas Announcements API](https://developerdocs.instructure.com/services/canvas/resources/announcements)
- [Canvas Courses API](https://developerdocs.instructure.com/services/canvas/resources/courses)
- [Canvas Discussion Topics/announcement fields](https://developerdocs.instructure.com/services/canvas/resources/discussion_topics)
- [Canvas Student Guide, including announcement RSS](https://community.canvaslms.com/html/assets/Canvas_Student_Guide.pdf)
- [Canvas notification preferences](https://developerdocs.instructure.com/services/canvas/resources/notification_preferences)
