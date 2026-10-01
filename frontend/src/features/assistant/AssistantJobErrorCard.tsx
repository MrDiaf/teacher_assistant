import { DiagnosticAssistantAction } from "../../platform/diagnostics";
import { Icon } from "../../platform/ui";
import type { AssistantJob } from "./types";

function friendlyJobError(message: string | null): string {
  if (!message) return "The assistant could not finish safely.";
  if (message.includes("OPENAI_API_KEY")) {
    return "The assistant was not connected. Sign in with ChatGPT, then retry safely.";
  }
  return message;
}

export function AssistantJobErrorCard({
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
        <DiagnosticAssistantAction errorId={job.diagnostic_error_id} />
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
