/** Shared parsing for the application's safe JSON error envelope. */

interface ApiErrorPayload {
  error_id?: string;
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
  request_id?: string;
  detail?: string | { msg?: string }[];
}

export class ApiError extends Error {
  readonly status: number;
  readonly errorId: string | null;
  readonly code: string | null;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(
    message: string,
    status: number,
    options: {
      errorId?: string;
      code?: string;
      details?: Record<string, unknown>;
      requestId?: string;
    } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorId = options.errorId ?? null;
    this.code = options.code ?? null;
    this.details = options.details ?? {};
    this.requestId = options.requestId ?? null;
  }
}

export async function parseApiResponse<T>(
  response: Response,
  fallbackMessage = "The request could not be completed.",
): Promise<T> {
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    const validationMessage = Array.isArray(payload?.detail)
      ? payload.detail[0]?.msg
      : payload?.detail;
    throw new ApiError(
      payload?.message ?? validationMessage ?? fallbackMessage,
      response.status,
      {
        errorId: payload?.error_id,
        code: payload?.code,
        details: payload?.details,
        requestId: payload?.request_id,
      },
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
