import { Icon } from "../../platform/ui";
import type { AssistantProposal, ProposalReviewItem } from "./types";

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

export function proposalStatusLabel(
  status: AssistantProposal["status"],
): string {
  return status.replaceAll("_", " ");
}

function proposalErrorCode(proposal: AssistantProposal): string | null {
  const code = proposal.result?.error_code;
  return typeof code === "string" && code ? code : null;
}

export function auditTime(value: string): string {
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

export function ProposalCard({
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
