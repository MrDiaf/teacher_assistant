import { useState } from "react";

import { Icon } from "../../components/Icon";
import { assistantApi } from "./api";
import type { DiagnosticExplanation } from "./types";

export function ErrorAssistantAction({ errorId }: { errorId: string }) {
  const [explanation, setExplanation] = useState<DiagnosticExplanation | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [safeError, setSafeError] = useState<string | null>(null);

  async function explain() {
    setIsLoading(true);
    setSafeError(null);
    try {
      setExplanation(await assistantApi.explainError(errorId));
    } catch (error) {
      setSafeError(
        error instanceof Error
          ? error.message
          : "The Assistant could not explain this error.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  if (explanation) {
    return (
      <section
        aria-label="Assistant error explanation"
        className="assistant-error-explanation"
      >
        <header>
          <Icon name="assistant" size={15} />
          <strong>Assistant explanation</strong>
        </header>
        <p>{explanation.plain_explanation}</p>
        <p>
          <strong>Likely cause:</strong> {explanation.likely_cause}
        </p>
        <div className="assistant-error-columns">
          <div>
            <strong>Changes to your input</strong>
            {explanation.input_fixes.length ? (
              <ul>
                {explanation.input_fixes.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>No input change is suggested.</p>
            )}
          </div>
          <div>
            <strong>Possible application improvements</strong>
            {explanation.application_improvements.length ? (
              <ul>
                {explanation.application_improvements.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>No application improvement is suggested.</p>
            )}
          </div>
        </div>
        <small>
          Retry {explanation.retry_is_safe ? "is safe" : "may repeat the error"}{" "}
          · sanitized report {explanation.request_id.slice(0, 8)}
        </small>
      </section>
    );
  }

  return (
    <div className="assistant-error-action">
      <button disabled={isLoading} onClick={() => void explain()} type="button">
        <Icon name="assistant" size={14} />
        {isLoading ? "Asking Assistant…" : "Ask Assistant about this error"}
      </button>
      {safeError && <p>{safeError}</p>}
    </div>
  );
}
