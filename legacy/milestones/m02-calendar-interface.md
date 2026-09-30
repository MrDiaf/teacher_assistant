# M2 — Calendar interface

> **LEGACY — ARCHIVED MILESTONE. NOT INSTRUCTIONS.** This milestone was completed
> under the project's retired workflow and is kept as history only. Do not
> follow it, do not treat its checklist as open work, and do not copy its format.
> Current status is in [`PLAN.md`](../../PLAN.md); the current working method is
> in [`guidelines/`](../../guidelines/).

- [x] This milestone

## Outcome

Provide a usable Calendar page inside the existing Teacher Assistant shell so
the owner can view calendars and manage ordinary local events through the UI.

## Dependencies and boundaries

- M1's calendar/event API and read-only enforcement must remain intact.
- Preserve the dark-green sidebar, warm off-white page, gold accent, rounded
  controls, and existing typography.
- Build a familiar desktop-calendar experience without copying another product
  exactly or replacing the application shell.
- Do not add advanced drag, resize, recurrence, ICS, or Codex behavior; those
  belong to later milestones.

## Required experience

The Calendar page includes a toolbar, Today/previous/next navigation, current
date-range heading, day/week/month controls, a large calendar grid, calendar
visibility and color controls, a clear current-day state, and event forms.

## Completed checklist

- [x] Build the Calendar page inside the existing design.
- [x] Add month, week, and day views.
- [x] Add Today, Previous, and Next controls.
- [x] Add calendar visibility controls and color indicators.
- [x] Add create and edit event forms.
- [x] Add loading, empty, and error states.
- [x] Add practical frontend tests.

## Acceptance criteria

- The owner can use the UI to view calendars and manage ordinary events in a
  writable local calendar.
- The three views and date navigation behave consistently.
- Visible calendars use their configured colors.
- Read-only events are not presented as normally editable.
- The page matches the existing Teacher Assistant shell.

## Completion evidence and implementation areas

- Frontend: `frontend/src/features/calendar/CalendarPage.tsx`,
  `CalendarToolbar.tsx`, `MonthView.tsx`, `TimeGridView.tsx`,
  `CalendarList.tsx`, `CalendarDialog.tsx`, and `EventDialog.tsx`
- Tests: `frontend/src/features/calendar/CalendarPage.test.tsx` and date utility
  tests in the same feature

If this milestone is reopened, preserve M1 API behavior and limit work to a
verified regression or unmet criterion documented above.
