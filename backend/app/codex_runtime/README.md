# Teacher Assistant Codex runtime

Each calendar-assistant or note-summary job gets a mode `0700` temporary root
outside the source repository. Calendar workspaces contain only bounded
calendar context. Summary workspaces contain only the note body and explicitly
linked slide text. Both contain the runtime policy and structured output schema.

The Codex app-server receives an allowlisted process environment. Its tool
subprocesses inherit no secrets. A named read-only permission profile allows
the minimum runtime paths and the job workspace, explicitly denies the source
repository and runtime socket paths, and disables tool network access.

## Authentication

The Assistant page uses Codex device authentication so the owner can sign in
with ChatGPT from a browser on the local network. Codex stores the renewable
session in its dedicated Docker volume under `CODEX_AUTH_HOME`. That directory
is mode `0700`, is never bind-mounted from the repository, and is explicitly
denied to runtime agent tools. The browser receives only the short-lived OpenAI
verification URL, user code, and safe status; it never receives access or
refresh tokens. `OPENAI_API_KEY` remains an optional usage-billed fallback.

## Retention

All runtime workspaces are deleted immediately after every job, whether it
completes, fails validation, times out, or raises an exception. Conversation
messages, final validated answers, validated proposals, confirmation state,
execution results, job state, and safe error messages remain in PostgreSQL;
temporary context files and model reasoning do not.
