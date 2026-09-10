# Inbox handoff

Current state: the M20 Inbox and mailbox Settings workflows are preserved.
M21A grouped `inbox` and `integrations` under one owner and recorded current
Settings/composition coupling; it changed no credential, mail, or remote state.
M21B now routes Inbox API/page composition through explicit public entries. Its
backend entry registers the unchanged credential/attachment root setup and mail
scheduler lifecycle.

Verification: [M21A baseline](../baseline.md). Feature evidence remains in
[M20](../../../milestones/m20-forwarded-mail-inbox.md). A real provider check
was not run because no owner credential is used in ordinary verification.

Next Inbox work: M21G consolidates public entries and contributed Settings after
M21F. The application-wide next step is M21B composition-test and boundary
tightening.
