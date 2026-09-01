# M20 — Integration secrets and Canvas connection

- [ ] This milestone

## Outcome

Turn Settings into a functional integration page and let the single owner link
one Canvas installation without exposing Canvas credentials to the browser or
repository. Prefer Canvas OAuth 2 when the institution enables an appropriate
developer key, while providing a clearly labelled manual-token fallback when
OAuth cannot be arranged.

M18 and M19 must be complete before this milestone starts. M20 establishes the
credential and connection boundary only; announcement ingestion belongs to
M21, and forwarded email belongs to M22.

## Supported connection paths

### Preferred: institution-approved OAuth 2

- The owner enters the exact HTTPS origin of the institution's Canvas instance.
- The institution administrator must create or enable a Canvas developer key
  with the exact Teacher Assistant callback URL and only the read scopes needed
  for profile, course-list, and announcement access.
- Request only `url:GET|/api/v1/users/:user_id/profile`,
  `url:GET|/api/v1/courses`, and `url:GET|/api/v1/announcements`. If a manually
  generated token cannot be scope-limited, the adapter must still call only
  these GET endpoints.
- The backend owns the authorization-code exchange, one-time `state`, token
  refresh, capability check, and disconnect/revocation flow. Bind each short-
  lived state record to the initiating browser flow and reject replay.
- The browser receives connection status and non-secret account metadata only;
  it never receives access tokens, refresh tokens, or the developer secret.
- Explain in setup documentation that a self-hosted clone does not automatically
  have a global Canvas developer key. Each institution controls whether this
  path is available.

### Compatible fallback: owner-created Canvas API token

- If the institution permits manually generated access tokens, let the owner
  paste a token once over a trusted loopback/LAN or HTTPS application
  connection.
- Validate it against the exact configured Canvas origin and required read
  endpoints before storing it.
- Never redisplay, echo, log, diagnose, or return the token after submission.
- Explain the wider lifetime/revocation tradeoff and show how to remove the
  local secret and revoke it in Canvas.
- Call this a manual supported-API fallback, not OAuth and not a promise that
  every institution enables personal tokens.

If neither method is available, direct the owner to the feed-only and
notification-email alternatives planned in M21 and M22. Do not accept a Canvas
password, browser cookie, session token, copied authorization header, or
automated HTML-login/scraping workflow.

## Private credential storage

- Add a generic backend-owned integration credential store under a configurable
  private root mounted as a persistent Docker volume.
- Store secret payloads in opaque files with private directory/file permissions,
  atomic replacement, and no path supplied by the browser. Database rows retain
  only a generated credential reference and safe connection metadata.
- Keep OAuth client secrets in private environment configuration; never persist
  them through the Settings API.
- Exclude renewable integration credentials from Git, diagnostics, logs, browser
  storage, Codex workspaces, ordinary database responses, and coordinated data
  backups. A clean restore requires reconnecting integrations.
- Missing, corrupt, incorrectly permissioned, or undecryptable credential files
  must produce a reconnect-required state rather than leaking content or
  crashing the application.
- Disconnect removes the local credential even if best-effort remote OAuth
  revocation is unavailable. It must not delete local courses, calendars, notes,
  announcements, or future inbox messages.

Do not reuse the Codex auth directory. Canvas/mail credentials and Codex login
state have separate lifecycles and permissions.

## Canvas client boundary

- Keep Canvas schemas, HTTP adapter, connection service, repository, API routes,
  and Settings UI separate.
- Normalize the configured origin and allow HTTPS only. Reject URL credentials,
  fragments, non-public/private network targets, DNS rebinding results, and
  redirects to another origin. Do not inherit proxy variables implicitly.
- Pin every API, token, refresh, pagination, and revoke request to the validated
  Canvas origin. Send bearer tokens only in the Authorization header.
- Use Canvas string-ID responses and store remote IDs as opaque strings.
- Follow opaque same-origin pagination links, make bounded sequential requests,
  honor rate-limit responses/backoff, and place timeouts and response-size
  limits on every external call.
- Record only sanitized status such as connected, reconnect required, last
  checked, allowed capabilities, and a bounded non-secret error.
- A capability probe may read the owner's profile and active course list. It
  must not import courses, assignments, files, grades, conversations, or
  announcements during M20.

## Settings workflow

```text
Owner opens Settings
    -> chooses Canvas
    -> enters the institution Canvas URL
    -> chooses OAuth or manual API token
    -> backend validates origin, authorization, and required read capabilities
    -> Settings shows connected account, method, scopes, and health
    -> owner may test, reconnect, or disconnect explicitly
```

The OAuth setup view must give the owner the exact callback URL and required
read scopes to send to the Canvas administrator. Connection errors should
distinguish invalid origin, administrator setup, denied consent, missing scope,
expired/revoked token, throttling, and transient Canvas failure without showing
secrets or raw upstream bodies.

## Completed checklist

- [ ] Define Canvas connection, credential-reference, and status schemas.
- [ ] Add the private integration credential root and Docker volume.
- [ ] Add atomic secret read/write/delete behavior with strict permissions.
- [ ] Add a validated, same-origin, bounded Canvas HTTP adapter.
- [ ] Implement OAuth authorization, callback, refresh, capability check, and
  best-effort revocation.
- [ ] Implement manual API-token validation, storage, replacement, and removal.
- [ ] Reject password, cookie, session-copy, and web-scraping connection paths.
- [ ] Make Settings a real page with connect, test, reconnect, and disconnect
  states.
- [ ] Add sanitized connection diagnostics and reconnect-required handling.
- [ ] Update backup/restore, `.env.example`, Docker, and owner setup docs.
- [ ] Add backend, frontend, security, accessibility, and E2E tests with a fake
  Canvas server; ordinary tests use no live school account.

## Acceptance criteria

- With an institution-approved developer key, the owner can complete OAuth and
  see a connected Canvas identity without any token reaching browser code.
- With OAuth unavailable but a permitted personal token, the owner can connect
  through the same least-privilege Canvas API boundary.
- Missing scopes, rejected consent, expired/revoked credentials, callback replay,
  state mismatch, hostile origins, redirects, and throttling fail safely.
- Refresh is serialized so concurrent requests do not corrupt or rotate away a
  valid credential.
- The Settings/status API and sanitized diagnostics contain no access token,
  refresh token, client secret, feed URL, cookie, or authorization header.
- Disconnect removes local authorization without deleting owner content.
- A clean restore starts in reconnect-required state and does not depend on
  copying renewable credentials.
- No Canvas data beyond the bounded identity/capability probe is imported.
- Existing calendar, course, Assistant, persistence, backup, and Docker behavior
  remains intact.

## Expected implementation areas

```text
backend/alembic/versions/<revision>_integration_connections.py
backend/app/integrations/{credentials,models,repository,routes,schemas,service}.py
backend/app/integrations/canvas/{client,oauth,schemas}.py
backend/app/core/config.py
backend/app/main.py
backend tests with a local fake Canvas service
frontend/src/features/settings/{SettingsPage,CanvasConnection,api,types}.tsx
frontend/src/App.tsx
frontend tests and e2e/tests/calendar-assistant.spec.ts
compose.yml
.env.example
scripts/data-{backup,restore}.sh
README.md
```

## Planning references

- [Canvas OAuth 2 overview](https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth)
- [Canvas OAuth 2 endpoints](https://developerdocs.instructure.com/services/canvas/oauth2/file.oauth_endpoints)
- [Canvas developer keys and scoped access](https://developerdocs.instructure.com/services/canvas/oauth2/file.developer_keys)
- [Canvas course-list API](https://developerdocs.instructure.com/services/canvas/resources/courses)
- [Canvas user-profile API](https://developerdocs.instructure.com/services/canvas/resources/users)
- [Canvas pagination](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
- [Canvas throttling](https://developerdocs.instructure.com/services/canvas/basics/file.throttling)
