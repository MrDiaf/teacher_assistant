import {
  Fragment,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { Icon } from "../../components/Icon";
import { AiModelSelector } from "../ai/AiModelSelector";
import { useAiModelSelection } from "../ai/useAiModelSelection";
import { assistantApi } from "./api";
import { ErrorAssistantAction } from "./ErrorAssistantAction";
import type {
  AssistantAuthStatus,
  AssistantConversation,
  AssistantDeviceLogin,
  AssistantJob,
  AssistantMessage,
  AssistantProposal,
  ProposalReviewItem,
} from "./types";

const SUGGESTIONS = [
  "What do I have tomorrow?",
  "Turn a topic into a study checklist.",
  "Explain what you can do with my course notes.",
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

function latestJob(jobs: AssistantJob[]): AssistantJob | null {
  return jobs.length ? jobs[jobs.length - 1] : null;
}

function thinkingMessage(elapsedSeconds: number): string {
  if (elapsedSeconds < 8) return "Thinking through your request…";
  if (elapsedSeconds < 18) return "Working with the relevant context…";
  if (elapsedSeconds < 30) {
    return "Validating the response before showing it…";
  }
  return `Still working (${elapsedSeconds}s). You can cancel at any time.`;
}

function AssistantJobErrorCard({
  job,
  isAuthenticated,
  onRetry,
}: {
  job: AssistantJob;
  isAuthenticated: boolean;
  onRetry: () => void;
}) {
  const details = job.safe_error_details ?? {};
  const reason = typeof details.reason === "string" ? details.reason : null;
  const ownerActions = Array.isArray(details.owner_actions)
    ? details.owner_actions.filter(
        (item): item is string => typeof item === "string" && Boolean(item),
      )
    : [];
  const developerActions = Array.isArray(details.developer_actions)
    ? details.developer_actions.filter(
        (item): item is string => typeof item === "string" && Boolean(item),
      )
    : [];
  const validationErrors = Array.isArray(details.validation_errors)
    ? details.validation_errors
    : [];
  const title =
    job.safe_error_code === "invalid_assistant_response"
      ? "The reply was blocked for safety"
      : "The assistant could not finish";

  return (
    <section className="assistant-job-error" role="alert">
      <header className="assistant-job-error-heading">
        <Icon name="refresh" size={18} />
        <div>
          <strong>{title}</strong>
          <p>{friendlyJobError(job.safe_error)}</p>
        </div>
      </header>

      {reason && reason !== job.safe_error && (
        <div className="assistant-job-error-section">
          <strong>Why it failed</strong>
          <p>{reason}</p>
        </div>
      )}
      {!reason && (
        <div className="assistant-job-error-section">
          <strong>Why details are limited</strong>
          <p>
            This failure was stored before detailed Assistant diagnostics were
            available. Retry once; if it fails again, the new attempt will show
            the exact validation stage and field issue.
          </p>
        </div>
      )}

      <div className="assistant-job-error-section">
        <strong>What you can do</strong>
        {ownerActions.length ? (
          <ul>
            {ownerActions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        ) : (
          <p>
            Retry once. If it fails again, rephrase the request or choose
            another model.
          </p>
        )}
      </div>

      <div className="assistant-job-error-actions">
        <button
          className="quiet-button"
          disabled={!isAuthenticated}
          onClick={onRetry}
          type="button"
        >
          Retry safely
        </button>
      </div>

      {job.diagnostic_error_id && (
        <ErrorAssistantAction errorId={job.diagnostic_error_id} />
      )}

      <details className="assistant-job-developer-details">
        <summary>Developer details</summary>
        <dl>
          <div>
            <dt>Error code</dt>
            <dd>{job.safe_error_code ?? "assistant_job_failed"}</dd>
          </div>
          {typeof details.failure_stage === "string" && (
            <div>
              <dt>Job stage</dt>
              <dd>{details.failure_stage}</dd>
            </div>
          )}
          {typeof details.validation_stage === "string" && (
            <div>
              <dt>Validation stage</dt>
              <dd>{details.validation_stage}</dd>
            </div>
          )}
          <div>
            <dt>Job reference</dt>
            <dd>{job.id}</dd>
          </div>
          {job.diagnostic_error_id && (
            <div>
              <dt>Diagnostic report</dt>
              <dd>{job.diagnostic_error_id}</dd>
            </div>
          )}
        </dl>
        {validationErrors.length > 0 && (
          <div className="assistant-job-validation-errors">
            <strong>Validation issues</strong>
            <ul>
              {validationErrors.map((item, index) => (
                <li key={`${item.field}-${item.type}-${index}`}>
                  <code>{item.field}</code>: {item.message} ({item.type})
                </li>
              ))}
            </ul>
          </div>
        )}
        {developerActions.length > 0 && (
          <ul className="assistant-job-developer-actions">
            {developerActions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        )}
      </details>
    </section>
  );
}

const REVIEW_FIELD_LABELS: Record<string, string> = {
  all_day: "All day",
  calendar_id: "Calendar",
  color: "Color",
  description: "Description",
  end_at: "Ends",
  location: "Location",
  name: "Name",
  recurrence_rule: "Repeats",
  start_at: "Starts",
  status: "Status",
  timezone: "Timezone",
  title: "Title",
};

function proposalStatusLabel(status: AssistantProposal["status"]): string {
  return status.replaceAll("_", " ");
}

function proposalErrorCode(proposal: AssistantProposal): string | null {
  const code = proposal.result?.error_code;
  return typeof code === "string" && code ? code : null;
}

function auditTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function reviewValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not set";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (
    typeof value === "string" &&
    (field === "start_at" || field === "end_at")
  ) {
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return new Intl.DateTimeFormat("en", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(parsed);
    }
  }
  return String(value);
}

function reviewChanges(item: ProposalReviewItem) {
  const previous = item.previous ?? {};
  const proposed = item.proposed ?? {};
  const fields = new Set([...Object.keys(previous), ...Object.keys(proposed)]);
  if (item.operation === "delete_event") {
    return ["title", "start_at", "end_at"].map((field) => ({
      field,
      before: previous[field],
      after: "Will be deleted",
    }));
  }
  return [...fields]
    .filter(
      (field) =>
        JSON.stringify(previous[field]) !== JSON.stringify(proposed[field]),
    )
    .map((field) => ({
      field,
      before: item.previous ? previous[field] : undefined,
      after: proposed[field],
    }));
}

interface ProposalCardProps {
  proposal: AssistantProposal;
  busy: boolean;
  onConfirm: () => void;
  onReject: () => void;
  onRevise: () => void;
}

function ProposalCard({
  proposal,
  busy,
  onConfirm,
  onReject,
  onRevise,
}: ProposalCardProps) {
  const awaiting = proposal.status === "awaiting_confirmation";
  const errorCode = proposalErrorCode(proposal);
  const isLinkedBatch = proposal.batch_count > 1;
  return (
    <section
      aria-label={`Calendar proposal: ${proposal.summary}`}
      className={`assistant-proposal-card ${proposal.status}`}
    >
      <header className="assistant-proposal-header">
        <span className="assistant-proposal-icon">
          <Icon name="checklist" size={18} />
        </span>
        <div>
          <small>
            Calendar change
            {isLinkedBatch &&
              ` · Batch ${proposal.batch_position} of ${proposal.batch_count}`}
          </small>
          <h3>{proposal.summary}</h3>
        </div>
        <span className="assistant-proposal-status">
          {proposalStatusLabel(proposal.status)}
        </span>
      </header>

      <div className="assistant-proposal-items">
        {proposal.review_items.map((item, index) => (
          <article
            key={`${item.operation}-${item.event_id ?? item.calendar_id}-${index}`}
          >
            <div className="assistant-proposal-item-heading">
              <strong>{item.title}</strong>
              <span>{item.calendar_name}</span>
            </div>
            <dl>
              {reviewChanges(item).map((change) => (
                <div key={change.field}>
                  <dt>{REVIEW_FIELD_LABELS[change.field] ?? change.field}</dt>
                  <dd>
                    {change.before !== undefined && (
                      <span>{reviewValue(change.field, change.before)}</span>
                    )}
                    {change.before !== undefined && <b aria-hidden="true">→</b>}
                    <strong>{reviewValue(change.field, change.after)}</strong>
                  </dd>
                </div>
              ))}
            </dl>
            <div className="assistant-proposal-item-meta">
              {item.recurrence_scope && (
                <span>
                  Recurrence: {item.recurrence_scope.replaceAll("_", " ")}
                </span>
              )}
              {item.affected_events > 0 && (
                <span>
                  {item.affected_events} affected event
                  {item.affected_events === 1 ? "" : "s"}
                </span>
              )}
            </div>
          </article>
        ))}
      </div>

      {proposal.warnings.length > 0 && (
        <ul className="assistant-proposal-warnings">
          {proposal.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
      {proposal.safe_error && (
        <p className="assistant-proposal-error" role="alert">
          <span>{proposal.safe_error}</span>
          <small>
            {errorCode && <>Error code: {errorCode}. </>}This safe failure is
            included automatically in your next assistant message.
          </small>
        </p>
      )}
      {awaiting && (
        <footer className="assistant-proposal-actions">
          <button disabled={busy} onClick={onConfirm} type="button">
            {busy
              ? "Working safely…"
              : isLinkedBatch
                ? `Confirm batch ${proposal.batch_position}`
                : "Confirm changes"}
          </button>
          <button disabled={busy} onClick={onRevise} type="button">
            {isLinkedBatch ? "Revise plan" : "Revise"}
          </button>
          <button disabled={busy} onClick={onReject} type="button">
            Reject
          </button>
        </footer>
      )}
      {!awaiting && proposal.status === "completed" && (
        <p className="assistant-proposal-result" role="status">
          Confirmed and completed by the calendar service.
        </p>
      )}
      <details className="assistant-proposal-audit">
        <summary>Audit details</summary>
        <ol>
          {proposal.action_records.map((record) => (
            <li key={record.id}>
              <strong>{record.operation.replaceAll("_", " ")}</strong>
              <span>
                Requested{" "}
                <time dateTime={record.requested_at}>
                  {auditTime(record.requested_at)}
                </time>
              </span>
              {record.confirmed_at && (
                <span>
                  Confirmed{" "}
                  <time dateTime={record.confirmed_at}>
                    {auditTime(record.confirmed_at)}
                  </time>
                </span>
              )}
              {record.executed_at && (
                <span>
                  Executed{" "}
                  <time dateTime={record.executed_at}>
                    {auditTime(record.executed_at)}
                  </time>
                </span>
              )}
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

export function AssistantPage() {
  const { modelList, selectedModel, setSelectedModel, modelError } =
    useAiModelSelection();
  const [conversations, setConversations] = useState<AssistantConversation[]>(
    [],
  );
  const [activeConversation, setActiveConversation] =
    useState<AssistantConversation | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [proposals, setProposals] = useState<AssistantProposal[]>([]);
  const [auditItems, setAuditItems] = useState<AssistantProposal[]>([]);
  const [sidebarMode, setSidebarMode] = useState<"conversations" | "activity">(
    "conversations",
  );
  const [isAuditLoading, setIsAuditLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [failedJob, setFailedJob] = useState<AssistantJob | null>(null);
  const [cancelledJob, setCancelledJob] = useState<AssistantJob | null>(null);
  const [busyProposalId, setBusyProposalId] = useState<string | null>(null);
  const [revisionProposal, setRevisionProposal] =
    useState<AssistantProposal | null>(null);
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
  const [isCancelling, setIsCancelling] = useState(false);
  const [thinkingSeconds, setThinkingSeconds] = useState(0);
  const [activeRequestConversationId, setActiveRequestConversationId] =
    useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const scrollAnchor = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const activeRequestController = useRef<AbortController | null>(null);
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
          setProposals(detail.proposals ?? []);
          const newestJob = latestJob(detail.jobs);
          setFailedJob(newestJob?.status === "failed" ? newestJob : null);
          setCancelledJob(newestJob?.status === "cancelled" ? newestJob : null);
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
    if (!isSending) {
      setThinkingSeconds(0);
      return;
    }
    const startedAt = Date.now();
    setThinkingSeconds(0);
    const timer = window.setInterval(() => {
      setThinkingSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isSending]);

  useEffect(() => {
    scrollAnchor.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, proposals, isSending, failedJob, cancelledJob]);

  async function loadConversation(conversation: AssistantConversation) {
    setError(null);
    setFailedJob(null);
    setCancelledJob(null);
    setRevisionProposal(null);
    setActiveConversation(conversation);
    try {
      const detail = await assistantApi.getConversation(conversation.id);
      setActiveConversation(detail);
      setMessages(detail.messages);
      setProposals(detail.proposals ?? []);
      const newestJob = latestJob(detail.jobs);
      setFailedJob(newestJob?.status === "failed" ? newestJob : null);
      setCancelledJob(newestJob?.status === "cancelled" ? newestJob : null);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "This conversation could not be loaded.",
      );
    }
  }

  async function showAudit() {
    setSidebarMode("activity");
    if (auditItems.length || isAuditLoading) return;
    setIsAuditLoading(true);
    setError(null);
    try {
      setAuditItems(await assistantApi.listAudit());
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Assistant activity could not be loaded.",
      );
    } finally {
      setIsAuditLoading(false);
    }
  }

  async function openAuditItem(proposal: AssistantProposal) {
    setError(null);
    try {
      const detail = await assistantApi.getConversation(
        proposal.conversation_id,
      );
      setActiveConversation(detail);
      setMessages(detail.messages);
      setProposals(detail.proposals ?? []);
      const newestJob = latestJob(detail.jobs);
      setFailedJob(newestJob?.status === "failed" ? newestJob : null);
      setCancelledJob(newestJob?.status === "cancelled" ? newestJob : null);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "This audit entry could not be opened.",
      );
    }
  }

  async function startConversation() {
    if (isSending) return;
    setError(null);
    setFailedJob(null);
    setCancelledJob(null);
    setRevisionProposal(null);
    try {
      const created = await assistantApi.createConversation();
      setConversations((current) => [created, ...current]);
      setActiveConversation(created);
      setMessages([]);
      setProposals([]);
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
    if (!selectedModel) {
      setError("Choose an allowed AI model before sending a message.");
      return;
    }
    setIsSending(true);
    setError(null);
    setFailedJob(null);
    setCancelledJob(null);
    setDraft("");
    let controller: AbortController | null = null;
    try {
      const conversation = await ensureConversation();
      controller = new AbortController();
      activeRequestController.current = controller;
      setActiveRequestConversationId(conversation.id);
      const optimisticMessage: AssistantMessage = {
        id: `pending-${Date.now()}`,
        conversation_id: conversation.id,
        role: "owner",
        content: normalized,
        citations: [],
        job_id: null,
        created_at: new Date().toISOString(),
      };
      setMessages((current) => [...current, optimisticMessage]);
      const turn = revisionProposal
        ? await assistantApi.reviseProposal(
            revisionProposal.id,
            normalized,
            selectedModel,
            controller.signal,
          )
        : await assistantApi.sendMessage(
            conversation.id,
            normalized,
            selectedModel,
            controller.signal,
          );
      const detail = await assistantApi.getConversation(conversation.id);
      setMessages(detail.messages);
      setProposals(detail.proposals ?? []);
      mergeAudit(detail.proposals ?? []);
      setRevisionProposal(null);
      setActiveConversation(turn.conversation);
      setConversations((current) => [
        turn.conversation,
        ...current.filter((item) => item.id !== turn.conversation.id),
      ]);
      setFailedJob(turn.job.status === "failed" ? turn.job : null);
      setCancelledJob(turn.job.status === "cancelled" ? turn.job : null);
    } catch (sendError) {
      if ((sendError as Error).name === "AbortError") return;
      setMessages((current) =>
        current.filter((message) => !message.id.startsWith("pending-")),
      );
      setError(
        sendError instanceof Error
          ? sendError.message
          : "The assistant could not answer safely.",
      );
    } finally {
      if (!controller || activeRequestController.current === controller) {
        if (controller) activeRequestController.current = null;
        setActiveRequestConversationId(null);
        setIsSending(false);
      }
    }
  }

  async function retry() {
    if (!failedJob || isSending || !isAuthenticated) return;
    setIsSending(true);
    setError(null);
    setCancelledJob(null);
    const controller = new AbortController();
    activeRequestController.current = controller;
    setActiveRequestConversationId(failedJob.conversation_id);
    try {
      const turn = await assistantApi.retryJob(failedJob.id, controller.signal);
      const detail = await assistantApi.getConversation(turn.conversation.id);
      setMessages(detail.messages);
      setProposals(detail.proposals ?? []);
      mergeAudit(detail.proposals ?? []);
      setFailedJob(turn.job.status === "failed" ? turn.job : null);
      setCancelledJob(turn.job.status === "cancelled" ? turn.job : null);
    } catch (retryError) {
      if ((retryError as Error).name === "AbortError") return;
      setError(
        retryError instanceof Error
          ? retryError.message
          : "The assistant retry failed safely.",
      );
    } finally {
      if (activeRequestController.current === controller) {
        activeRequestController.current = null;
        setActiveRequestConversationId(null);
        setIsSending(false);
      }
    }
  }

  async function cancelRequest() {
    const conversationId = activeRequestConversationId;
    const controller = activeRequestController.current;
    if (!conversationId || !controller || isCancelling) return;
    setIsCancelling(true);
    setError(null);
    try {
      const job = await assistantApi.cancelConversation(conversationId);
      if (job.status === "cancelled") {
        controller.abort();
      }
      const detail = await assistantApi.getConversation(conversationId);
      setMessages(detail.messages);
      setProposals(detail.proposals ?? []);
      mergeAudit(detail.proposals ?? []);
      const newestJob = latestJob(detail.jobs);
      setFailedJob(newestJob?.status === "failed" ? newestJob : null);
      setCancelledJob(newestJob?.status === "cancelled" ? newestJob : null);
    } catch (cancelError) {
      setError(
        cancelError instanceof Error
          ? cancelError.message
          : "The Assistant request could not be cancelled.",
      );
    } finally {
      if (activeRequestController.current === controller) {
        activeRequestController.current = null;
      }
      setActiveRequestConversationId(null);
      setIsSending(false);
      setIsCancelling(false);
    }
  }

  function mergeAudit(items: AssistantProposal[]) {
    setAuditItems((current) => {
      const incomingIds = new Set(items.map((proposal) => proposal.id));
      return [
        ...items,
        ...current.filter((proposal) => !incomingIds.has(proposal.id)),
      ].sort(
        (left, right) =>
          new Date(right.updated_at).getTime() -
          new Date(left.updated_at).getTime(),
      );
    });
  }

  function replaceProposal(updated: AssistantProposal) {
    setProposals((current) =>
      current.map((proposal) =>
        proposal.id === updated.id ? updated : proposal,
      ),
    );
    mergeAudit([updated]);
  }

  async function confirmProposal(proposal: AssistantProposal) {
    if (busyProposalId) return;
    setBusyProposalId(proposal.id);
    setError(null);
    try {
      replaceProposal(await assistantApi.confirmProposal(proposal.id));
    } catch (proposalError) {
      setError(
        proposalError instanceof Error
          ? proposalError.message
          : "The proposal could not be confirmed safely.",
      );
    } finally {
      setBusyProposalId(null);
    }
  }

  async function rejectProposal(proposal: AssistantProposal) {
    if (busyProposalId) return;
    setBusyProposalId(proposal.id);
    setError(null);
    try {
      replaceProposal(await assistantApi.rejectProposal(proposal.id));
    } catch (proposalError) {
      setError(
        proposalError instanceof Error
          ? proposalError.message
          : "The proposal could not be rejected safely.",
      );
    } finally {
      setBusyProposalId(null);
    }
  }

  function reviseProposal(proposal: AssistantProposal) {
    setRevisionProposal(proposal);
    setDraft("");
    window.setTimeout(() => composer.current?.focus(), 0);
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
          <p className="eyebrow">Private AI workspace</p>
          <h1 id="assistant-title">Assistant</h1>
          <p>
            Ask general questions, or work with your calendar and course notes.
          </p>
        </div>
        <div className="assistant-mode-badge">
          <Icon name="checklist" size={15} />
          <span>
            <strong>Confirmation mode</strong>
            <small>Nothing changes without your approval</small>
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
              <h2>
                {sidebarMode === "activity" ? "Activity" : "Conversations"}
              </h2>
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
          <div
            className="assistant-sidebar-tabs"
            role="tablist"
            aria-label="Assistant history"
          >
            <button
              aria-selected={sidebarMode === "conversations"}
              onClick={() => setSidebarMode("conversations")}
              role="tab"
              type="button"
            >
              Conversations
            </button>
            <button
              aria-selected={sidebarMode === "activity"}
              onClick={() => void showAudit()}
              role="tab"
              type="button"
            >
              Activity
            </button>
          </div>
          {sidebarMode === "conversations" ? (
            <div className="conversation-list" role="tabpanel">
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
          ) : (
            <div className="assistant-audit-list" role="tabpanel">
              {isAuditLoading ? (
                <div className="assistant-history-loading" role="status">
                  Loading activity…
                </div>
              ) : auditItems.length === 0 ? (
                <p className="conversation-list-empty">
                  Confirmed and rejected proposals appear here.
                </p>
              ) : (
                auditItems.map((proposal) => (
                  <button
                    key={proposal.id}
                    onClick={() => void openAuditItem(proposal)}
                    type="button"
                  >
                    <span
                      className={`assistant-audit-status ${proposal.status}`}
                    />
                    <span>
                      <strong>{proposal.summary}</strong>
                      <small>
                        {proposalStatusLabel(proposal.status)} ·{" "}
                        {auditTime(proposal.updated_at)}
                      </small>
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
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
              General help uses model knowledge. Calendar and relevant note
              context stay private to this installation.
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
                  I can help with general questions, explanations, writing,
                  planning, study aids, and code snippets. I can also use your
                  calendar and relevant course notes; every calendar change
                  still waits for your confirmation.
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

            {(messages.length > 0 ||
              isSending ||
              failedJob ||
              cancelledJob) && (
              <div className="assistant-message-list">
                {messages.map((message) => {
                  const messageProposals = proposals
                    .filter((item) => item.job_id === message.job_id)
                    .sort(
                      (left, right) =>
                        left.batch_position - right.batch_position,
                    );
                  const isLinkedPlan = messageProposals.length > 1;
                  const totalAffectedEvents = messageProposals.reduce(
                    (total, proposal) => total + proposal.affected_events,
                    0,
                  );
                  const resolvedBatches = messageProposals.filter(
                    (proposal) =>
                      proposal.status !== "awaiting_confirmation" &&
                      proposal.status !== "confirmed" &&
                      proposal.status !== "executing",
                  ).length;
                  return (
                    <Fragment key={message.id}>
                      <article className={`assistant-message ${message.role}`}>
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
                              {message.role === "assistant"
                                ? "Assistant"
                                : "You"}
                            </strong>
                            <time dateTime={message.created_at}>
                              {messageTime(message.created_at)}
                            </time>
                          </header>
                          <p>{message.content}</p>
                          {message.citations.length > 0 && (
                            <ul
                              aria-label="Course note citations"
                              className="assistant-citations"
                            >
                              {message.citations.map((citation) => (
                                <li
                                  key={[
                                    citation.note_id,
                                    citation.source_id,
                                    citation.slide_number,
                                  ].join("-")}
                                >
                                  <Icon name="file" size={12} />
                                  <span>
                                    {citation.course_name} ·{" "}
                                    {citation.note_title}
                                    {citation.source_name &&
                                      citation.slide_number && (
                                        <>
                                          {" "}
                                          · {citation.source_name}, slide{" "}
                                          {citation.slide_number}
                                        </>
                                      )}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </article>
                      {isLinkedPlan && (
                        <section
                          aria-label="Linked calendar plan"
                          className="assistant-proposal-plan"
                        >
                          <div>
                            <strong>Linked calendar plan</strong>
                            <span>
                              {totalAffectedEvents} event
                              {totalAffectedEvents === 1 ? "" : "s"} across{" "}
                              {messageProposals.length} separately confirmed
                              batches
                            </span>
                          </div>
                          <span>
                            {resolvedBatches} of {messageProposals.length}{" "}
                            resolved
                          </span>
                        </section>
                      )}
                      {messageProposals.map((proposal) => (
                        <ProposalCard
                          busy={busyProposalId === proposal.id}
                          key={proposal.id}
                          onConfirm={() => void confirmProposal(proposal)}
                          onReject={() => void rejectProposal(proposal)}
                          onRevise={() => reviseProposal(proposal)}
                          proposal={proposal}
                        />
                      ))}
                    </Fragment>
                  );
                })}
                {isSending && (
                  <div className="assistant-thinking" role="status">
                    <div className="assistant-thinking-dots" aria-hidden="true">
                      <span />
                      <span />
                      <span />
                    </div>
                    <div className="assistant-thinking-copy">
                      <strong>{thinkingMessage(thinkingSeconds)}</strong>
                      <small>
                        Invalid response formatting is corrected automatically
                        once before an error is shown.
                      </small>
                    </div>
                    <button
                      className="quiet-button"
                      disabled={!activeRequestConversationId || isCancelling}
                      onClick={() => void cancelRequest()}
                      type="button"
                    >
                      {isCancelling ? "Cancelling…" : "Cancel request"}
                    </button>
                  </div>
                )}
                {cancelledJob && !isSending && (
                  <section className="assistant-job-cancelled" role="status">
                    <Icon name="x" size={17} />
                    <div>
                      <strong>Request cancelled</strong>
                      <p>
                        No Assistant answer or calendar change was saved. You
                        can send the request again whenever you are ready.
                      </p>
                    </div>
                    <button
                      className="quiet-button"
                      onClick={() => setCancelledJob(null)}
                      type="button"
                    >
                      Dismiss
                    </button>
                  </section>
                )}
                {failedJob && !isSending && (
                  <AssistantJobErrorCard
                    isAuthenticated={isAuthenticated}
                    job={failedJob}
                    onRetry={() => void retry()}
                  />
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
          {modelError && (
            <p className="assistant-page-error" role="alert">
              {modelError}
            </p>
          )}

          <form className="assistant-composer" onSubmit={submit}>
            {revisionProposal && (
              <div className="assistant-revision-notice">
                <span>
                  Revising: <strong>{revisionProposal.summary}</strong>
                </span>
                <button
                  aria-label="Cancel proposal revision"
                  onClick={() => setRevisionProposal(null)}
                  type="button"
                >
                  <Icon name="x" size={14} />
                </button>
              </div>
            )}
            <AiModelSelector
              disabled={isSending}
              modelList={modelList}
              onChange={setSelectedModel}
              value={selectedModel}
            />
            <label className="sr-only" htmlFor="assistant-message">
              Message the Assistant
            </label>
            <textarea
              disabled={isSending || !isAuthenticated || !selectedModel}
              id="assistant-message"
              maxLength={4000}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder={
                isAuthenticated
                  ? revisionProposal
                    ? "Describe what should change in the proposal…"
                    : "Ask anything, or use your calendar and notes…"
                  : "Sign in with ChatGPT to ask the Assistant"
              }
              ref={composer}
              rows={2}
              value={draft}
            />
            <button
              aria-label="Send message"
              disabled={
                isSending || !isAuthenticated || !selectedModel || !draft.trim()
              }
              type="submit"
            >
              <Icon name="send" size={18} />
            </button>
            <small>
              {isAuthenticated
                ? revisionProposal
                  ? "Sending this will reject the old proposal and request a revised one"
                  : "Enter to send · Shift+Enter for a new line"
                : "Connect ChatGPT above to enable the assistant"}
            </small>
          </form>
        </div>
      </section>
    </main>
  );
}
