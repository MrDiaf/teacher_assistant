# M19 — Frontend navigation and Assistant-draft persistence

> **LEGACY — ARCHIVED MILESTONE. NOT INSTRUCTIONS.** This milestone was completed
> under the project's retired workflow and is kept as history only. Do not
> follow it, do not treat its checklist as open work, and do not copy its format.
> Current status is in [`PLAN.md`](../../PLAN.md); the current working method is
> in [`guidelines/`](../../guidelines/).

- [x] This milestone

## Outcome

Remember useful frontend navigation state when the owner leaves a module and
returns. In particular, Calendar must reopen in the previously selected
day/week/month view, and unsent Assistant text must still be present after
visiting another module.

This is limited persistence of owner-controlled UI state. It is not a cache of
authoritative API data and must not create a second source of truth for
calendars, courses, notes, messages, proposals, or permissions.

## State to remember

Persist a small, versioned, namespaced set of values:

- last active top-level module;
- main Calendar view (`day`, `week`, or `month`) and anchor date;
- course Calendar view and anchor date, scoped by course ID;
- selected course ID and selected course tab;
- selected Assistant conversation and conversation/activity sidebar mode;
- unsent Assistant composer text, separately for each conversation and for a
  not-yet-created conversation.

When a saved course, calendar, conversation, or summary no longer exists, fall
back safely and remove the stale preference. The Today button must still reset
the calendar anchor normally.

## State not to remember

Do not persist:

- credentials, ChatGPT device-login data, tokens, cookies, or headers;
- fetched event, note, source, summary, conversation, or proposal payloads;
- read-only permission decisions or backend validation results;
- active requests, timers, cancellation controllers, busy/error states, undo
  actions, modal dialogs, or destructive confirmations;
- unsaved event/course/source deletion forms;
- note and summary expanded/minimized state—M17 intentionally starts every note
  and summary minimized whenever the Notes view mounts;
- Codex runtime context or raw model output.

Every authoritative record must still be reloaded from FastAPI when its page is
opened.

## Browser-storage behavior

- Use a centralized typed persistence helper or hooks rather than scattered raw
  `localStorage` calls.
- Namespace and version keys so incompatible future schemas can be discarded.
- Validate every restored value against allowed modules, tabs, views, UUID/date
  formats, and size limits before using it.
- Treat unavailable, disabled, full, corrupt, or manually edited browser
  storage as a normal fallback to defaults.
- Keep Assistant drafts only in this browser profile/origin and never send them
  until the owner presses Send.
- Clear the relevant draft only after a successful send handoff; retain it on
  validation, authentication, network, timeout, or runtime failure.
- Provide an explicit way to clear the current Assistant draft.
- Cap stored draft count and size without silently removing the active draft.
- Do not log draft text or include it in diagnostics.

Use durable browser storage for the requested return behavior. Document that
clearing site data or using another browser/device removes this convenience
state but does not delete backend records.

## Component behavior

Current module pages unmount when navigation changes, so their local React
state resets. Restore persisted values during initial state creation or through
a shared state layer without briefly overwriting them with defaults.

Switching Assistant conversations must save the old conversation's draft before
loading the new draft. Starting a new conversation must not erase another
conversation's unsent text. A successfully sent draft clears only its matching
conversation key.

Restoration must not trigger duplicate API requests, send a message, open a
dialog, execute a proposal, or mutate calendar data.

## Completed checklist

- [x] Define and document the versioned persisted-state schema and privacy
  boundary.
- [x] Add a typed, validated browser-storage helper with graceful fallback.
- [x] Persist and restore the active application module.
- [x] Persist and restore main/course Calendar view and anchor state.
- [x] Persist and restore selected course and course tab.
- [x] Persist and restore Assistant conversation/sidebar selection.
- [x] Persist Assistant drafts per conversation and for a new conversation.
- [x] Clear only successfully sent or explicitly cleared drafts.
- [x] Confirm M17 note/summary expansion state is not persisted and still
  resets to minimized on every Notes-view mount.
- [x] Remove stale identifiers and reject malformed stored values.
- [x] Add privacy, size-limit, and storage-failure behavior.
- [x] Add unmount/remount, reload, multi-conversation, and accessibility tests.
- [x] Add E2E navigation-return scenarios and update documentation.

## Acceptance criteria

- Select Calendar Day, navigate to Assistant, return to Calendar, and remain in
  Day view at the remembered anchor date.
- Type unsent Assistant text, visit Calendar or Courses, return, and see the
  exact text in the correct conversation.
- Drafts for two conversations remain distinct.
- A successful send clears only the sent conversation's draft; a failed send
  retains it.
- Returning to Courses restores the selected existing course and tab.
- Returning to the Notes tab does not restore expanded note/summary panels;
  every panel starts minimized as required by M17.
- Invalid or stale stored values fall back without crashing or hiding data.
- Reloading a page restores supported UI state but always reloads authoritative
  records and permissions from the backend.
- No credentials, fetched private datasets, proposals, or active-operation
  state is placed in browser persistence.
- Existing cancellation, read-only, confirmation, undo, and accessibility
  behavior remains intact.
- Relevant unit, integration, E2E, lint, and production build checks pass.

## Expected implementation areas

```text
frontend/src/App.tsx
frontend/src/components/AppShell.tsx
frontend/src/hooks/usePersistentState.ts or equivalent
frontend/src/features/calendar/CalendarPage.tsx
frontend/src/features/courses/CoursesPage.tsx
frontend/src/features/courses/CourseCalendar.tsx
frontend/src/features/courses/CourseNotes.tsx
frontend/src/features/assistant/AssistantPage.tsx
frontend tests and e2e/tests/calendar-assistant.spec.ts
README.md
```

Offline API caching, service workers, cross-device synchronization, and saving
unfinished destructive forms are outside this milestone.
