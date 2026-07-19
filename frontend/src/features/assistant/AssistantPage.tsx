import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { Icon } from "../../components/Icon";
import { assistantApi } from "./api";
import type {
  AssistantAuthStatus,
  AssistantConversation,
  AssistantDeviceLogin,
  AssistantJob,
  AssistantMessage,
} from "./types";

const SUGGESTIONS = [
  "What do I have tomorrow?",
  "Which calendars are read-only?",
  "Find a free hour after 16:00 this week.",
];

function messageTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function friendlyJobError(message: string | null): string {
  if (!message) return "The assistant could not finish safely.";
  if (message.includes("OPENAI_API_KEY")) {
    return "The assistant was not connected. Sign in with ChatGPT, then retry safely.";
  }
  return message;
}

export function AssistantPage() {
  const [conversations, setConversations] = useState<AssistantConversation[]>(
    [],
  );
  const [activeConversation, setActiveConversation] =
    useState<AssistantConversation | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [failedJob, setFailedJob] = useState<AssistantJob | null>(null);
  const [authStatus, setAuthStatus] = useState<AssistantAuthStatus | null>(
    null,
  );
  const [loginAttempt, setLoginAttempt] = useState<AssistantDeviceLogin | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isAuthBusy, setIsAuthBusy] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const scrollAnchor = useRef<HTMLDivElement>(null);
  const isAuthenticated = authStatus?.authenticated === true;

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const loaded = await assistantApi.listConversations(controller.signal);
        setConversations(loaded);
        if (loaded[0]) {
          const detail = await assistantApi.getConversation(
            loaded[0].id,
            controller.signal,
          );
          setActiveConversation(detail);
          setMessages(detail.messages);
          setFailedJob(
            [...detail.jobs].reverse().find((job) => job.status === "failed") ??
              null,
          );
        }
      } catch (loadError) {
        if ((loadError as Error).name !== "AbortError") {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Conversations could not be loaded.",
          );
        }
      } finally {
        setIsLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function loadAuth() {
      try {
        setAuthStatus(await assistantApi.getAuthStatus(controller.signal));
      } catch (loadError) {
        if ((loadError as Error).name !== "AbortError") {
          setAuthError(
            loadError instanceof Error
              ? loadError.message
              : "ChatGPT connection status could not be loaded.",
          );
        }
      } finally {
        setIsAuthLoading(false);
      }
    }
    void loadAuth();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!loginAttempt || loginAttempt.status !== "pending") return;
    const controller = new AbortController();
    let timer = 0;

    async function poll() {
      try {
        const latest = await assistantApi.getDeviceLogin(
          loginAttempt!.login_id,
          controller.signal,
        );
        setLoginAttempt(latest);
        if (latest.status === "completed") {
          const connected = await assistantApi.getAuthStatus(controller.signal);
          setAuthStatus(connected);
          if (connected.authenticated) setLoginAttempt(null);
          return;
        }
        if (latest.status === "failed") return;
        timer = window.setTimeout(() => void poll(), 1200);
      } catch (pollError) {
        if ((pollError as Error).name !== "AbortError") {
          setLoginAttempt((current) =>
            current
              ? {
                  ...current,
                  status: "failed",
                  safe_error:
                    "The sign-in check was interrupted. Start a new attempt.",
                }
              : current,
          );
          setAuthError(
            pollError instanceof Error
              ? pollError.message
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
  }, [loginAttempt?.login_id, loginAttempt?.status]);

  useEffect(() => {
    scrollAnchor.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, isSending, failedJob]);

  async function loadConversation(conversation: AssistantConversation) {
    setError(null);
    setFailedJob(null);
    setActiveConversation(conversation);
    try {
      const detail = await assistantApi.getConversation(conversation.id);
      setActiveConversation(detail);
      setMessages(detail.messages);
      setFailedJob(
        [...detail.jobs].reverse().find((job) => job.status === "failed") ??
          null,
      );
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "This conversation could not be loaded.",
      );
    }
  }

  async function startConversation() {
    if (isSending) return;
    setError(null);
    setFailedJob(null);
    try {
      const created = await assistantApi.createConversation();
      setConversations((current) => [created, ...current]);
      setActiveConversation(created);
      setMessages([]);
      setDraft("");
    } catch (createError) {
      setError(
        createError instanceof Error
          ? createError.message
          : "A conversation could not be created.",
      );
    }
  }

  async function ensureConversation(): Promise<AssistantConversation> {
    if (activeConversation) return activeConversation;
    const created = await assistantApi.createConversation();
    setActiveConversation(created);
    setConversations((current) => [created, ...current]);
    return created;
  }

  async function send(content: string) {
    const normalized = content.trim();
    if (!normalized || isSending) return;
    if (!isAuthenticated) {
      setError("Sign in with ChatGPT before sending a message.");
      return;
    }
    setIsSending(true);
    setError(null);
    setFailedJob(null);
    setDraft("");
    try {
      const conversation = await ensureConversation();
      const optimisticMessage: AssistantMessage = {
        id: `pending-${Date.now()}`,
        conversation_id: conversation.id,
        role: "owner",
        content: normalized,
        job_id: null,
        created_at: new Date().toISOString(),
      };
      setMessages((current) => [...current, optimisticMessage]);
      const turn = await assistantApi.sendMessage(conversation.id, normalized);
      const detail = await assistantApi.getConversation(conversation.id);
      setMessages(detail.messages);
      setActiveConversation(turn.conversation);
      setConversations((current) => [
        turn.conversation,
        ...current.filter((item) => item.id !== turn.conversation.id),
      ]);
      if (turn.job.status === "failed") {
        setFailedJob(turn.job);
      } else {
        setFailedJob(null);
      }
    } catch (sendError) {
      setMessages((current) =>
        current.filter((message) => !message.id.startsWith("pending-")),
      );
      setError(
        sendError instanceof Error
          ? sendError.message
          : "The assistant could not answer safely.",
      );
    } finally {
      setIsSending(false);
    }
  }

  async function retry() {
    if (!failedJob || isSending || !isAuthenticated) return;
    setIsSending(true);
    setError(null);
    try {
      const turn = await assistantApi.retryJob(failedJob.id);
      const detail = await assistantApi.getConversation(turn.conversation.id);
      setMessages(detail.messages);
      setFailedJob(turn.job.status === "failed" ? turn.job : null);
    } catch (retryError) {
      setError(
        retryError instanceof Error
          ? retryError.message
          : "The assistant retry failed safely.",
      );
    } finally {
      setIsSending(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(draft);
    }
  }

  async function startSignIn() {
    if (isAuthBusy) return;
    setIsAuthBusy(true);
    setAuthError(null);
    try {
      setLoginAttempt(await assistantApi.startDeviceLogin());
    } catch (signInError) {
      setAuthError(
        signInError instanceof Error
          ? signInError.message
          : "ChatGPT sign-in could not start.",
      );
    } finally {
      setIsAuthBusy(false);
    }
  }

  async function signOut() {
    if (isAuthBusy) return;
    setIsAuthBusy(true);
    setAuthError(null);
    try {
      setAuthStatus(await assistantApi.logout());
      setLoginAttempt(null);
    } catch (signOutError) {
      setAuthError(
        signOutError instanceof Error
          ? signOutError.message
          : "ChatGPT could not be signed out safely.",
      );
    } finally {
      setIsAuthBusy(false);
    }
  }

  return (
    <main className="assistant-page" aria-labelledby="assistant-title">
      <header className="assistant-page-header">
        <div>
          <p className="eyebrow">Calendar intelligence</p>
          <h1 id="assistant-title">Assistant</h1>
          <p>Ask about your schedule and availability in plain language.</p>
        </div>
        <div className="assistant-mode-badge">
          <Icon name="lock" size={15} />
          <span>
            <strong>Read-only mode</strong>
            <small>Answers cannot change calendar data</small>
          </span>
        </div>
      </header>

      <section className="assistant-shell">
        <aside
          className="conversation-panel"
          aria-label="Assistant conversations"
        >
          <div className="conversation-panel-heading">
            <div>
              <p className="eyebrow">History</p>
              <h2>Conversations</h2>
            </div>
            <button
              aria-label="New conversation"
              className="calendar-add-button"
              disabled={isSending}
              onClick={() => void startConversation()}
              type="button"
            >
              <Icon name="plus" size={15} />
            </button>
          </div>
          <div className="conversation-list">
            {isLoading ? (
              <div className="assistant-history-loading" role="status">
                Loading conversations…
              </div>
            ) : conversations.length === 0 ? (
              <p className="conversation-list-empty">
                Your saved conversations appear here.
              </p>
            ) : (
              conversations.map((conversation) => (
                <button
                  className={
                    conversation.id === activeConversation?.id ? "active" : ""
                  }
                  key={conversation.id}
                  onClick={() => void loadConversation(conversation)}
                  type="button"
                >
                  <Icon name="assistant" size={16} />
                  <span>
                    <strong>{conversation.title}</strong>
                    <small>
                      {new Intl.DateTimeFormat("en", {
                        month: "short",
                        day: "numeric",
                      }).format(new Date(conversation.updated_at))}
                    </small>
                  </span>
                </button>
              ))
            )}
          </div>
          {isAuthenticated && (
            <div className="assistant-account-summary">
              <span className="assistant-account-dot" aria-hidden="true" />
              <div>
                <strong>
                  {authStatus?.auth_type === "chatgpt"
                    ? "ChatGPT connected"
                    : "API key connected"}
                </strong>
                <small>
                  {authStatus?.email ??
                    authStatus?.plan_type?.replaceAll("_", " ") ??
                    "Assistant ready"}
                </small>
              </div>
              {authStatus?.auth_type === "chatgpt" && (
                <button
                  disabled={isAuthBusy}
                  onClick={() => void signOut()}
                  type="button"
                >
                  Sign out
                </button>
              )}
            </div>
          )}
          <div className="assistant-context-note">
            <Icon name="calendar" size={16} />
            <span>
              Answers use calendar context from this private installation.
            </span>
          </div>
        </aside>

        <div className="assistant-chat-panel">
          <div className="assistant-messages" aria-live="polite">
            {isAuthLoading && (
              <div className="assistant-auth-loading" role="status">
                Checking ChatGPT connection…
              </div>
            )}

            {!isAuthLoading && !isAuthenticated && (
              <section
                className={
                  messages.length
                    ? "assistant-auth-card compact"
                    : "assistant-auth-card"
                }
                aria-labelledby="assistant-auth-title"
              >
                <span className="assistant-welcome-icon">
                  <Icon name="assistant" size={30} />
                </span>
                <p className="eyebrow">Connect your account</p>
                <h2 id="assistant-auth-title">Use your ChatGPT subscription</h2>
                <p>
                  Sign in with ChatGPT through OpenAI. Teacher Assistant stores
                  the renewable Codex session privately on this server—your
                  password never passes through this app.
                </p>

                {loginAttempt?.status === "pending" ? (
                  <div className="assistant-device-login" role="status">
                    <a
                      href={loginAttempt.verification_url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Open OpenAI sign-in
                    </a>
                    <span>Then enter this one-time code:</span>
                    <code aria-label="ChatGPT device code">
                      {loginAttempt.user_code}
                    </code>
                    <small>Waiting for you to finish in the new tab…</small>
                  </div>
                ) : (
                  <button
                    className="assistant-auth-button"
                    disabled={isAuthBusy}
                    onClick={() => void startSignIn()}
                    type="button"
                  >
                    {isAuthBusy
                      ? "Starting secure sign-in…"
                      : loginAttempt?.status === "failed"
                        ? "Start sign-in again"
                        : "Sign in with ChatGPT"}
                  </button>
                )}

                {loginAttempt?.status === "failed" && (
                  <p className="assistant-auth-inline-error" role="alert">
                    {loginAttempt.safe_error}
                  </p>
                )}
                <small className="assistant-auth-note">
                  Device sign-in is used because Teacher Assistant runs on your
                  local server. An API key is not required.
                </small>
              </section>
            )}

            {isAuthenticated && messages.length === 0 && !isSending && (
              <div className="assistant-welcome">
                <span className="assistant-welcome-icon">
                  <Icon name="assistant" size={30} />
                </span>
                <p className="eyebrow">Ready when you are</p>
                <h2>What would you like to know?</h2>
                <p>
                  I can explain your schedule, identify protected calendars, and
                  help find free time. Calendar changes arrive in a later
                  milestone.
                </p>
                <div className="assistant-suggestions">
                  {SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => void send(suggestion)}
                      type="button"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {(messages.length > 0 || isSending || failedJob) && (
              <div className="assistant-message-list">
                {messages.map((message) => (
                  <article
                    className={`assistant-message ${message.role}`}
                    key={message.id}
                  >
                    <div className="assistant-message-avatar">
                      {message.role === "assistant" ? (
                        <Icon name="assistant" size={17} />
                      ) : (
                        "You"
                      )}
                    </div>
                    <div>
                      <header>
                        <strong>
                          {message.role === "assistant" ? "Assistant" : "You"}
                        </strong>
                        <time dateTime={message.created_at}>
                          {messageTime(message.created_at)}
                        </time>
                      </header>
                      <p>{message.content}</p>
                    </div>
                  </article>
                ))}
                {isSending && (
                  <div className="assistant-thinking" role="status">
                    <span />
                    <span />
                    <span />
                    <strong>Checking your calendar safely…</strong>
                  </div>
                )}
                {failedJob && !isSending && (
                  <div className="assistant-job-error" role="alert">
                    <Icon name="refresh" size={18} />
                    <div>
                      <strong>The assistant could not finish</strong>
                      <p>{friendlyJobError(failedJob.safe_error)}</p>
                    </div>
                    <button
                      className="quiet-button"
                      disabled={!isAuthenticated}
                      onClick={() => void retry()}
                      type="button"
                    >
                      Retry safely
                    </button>
                  </div>
                )}
              </div>
            )}
            <div ref={scrollAnchor} />
          </div>

          {error && (
            <p className="assistant-page-error" role="alert">
              {error}
            </p>
          )}
          {authError && (
            <p className="assistant-page-error" role="alert">
              {authError}
            </p>
          )}

          <form className="assistant-composer" onSubmit={submit}>
            <label className="sr-only" htmlFor="assistant-message">
              Message the calendar assistant
            </label>
            <textarea
              disabled={isSending || !isAuthenticated}
              id="assistant-message"
              maxLength={4000}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder={
                isAuthenticated
                  ? "Ask about your calendar…"
                  : "Sign in with ChatGPT to ask about your calendar"
              }
              rows={2}
              value={draft}
            />
            <button
              aria-label="Send message"
              disabled={isSending || !isAuthenticated || !draft.trim()}
              type="submit"
            >
              <Icon name="send" size={18} />
            </button>
            <small>
              {isAuthenticated
                ? "Enter to send · Shift+Enter for a new line"
                : "Connect ChatGPT above to enable the assistant"}
            </small>
          </form>
        </div>
      </section>
    </main>
  );
}
