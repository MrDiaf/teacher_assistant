import type {
  CalendarEvent,
  CalendarModel,
  CalendarMutation,
  EventMutation,
  EventUpdateMutation,
  IcsImportOptions,
  IcsImportResult,
  IcsPreview,
  IcsSubscriptionOptions,
} from "./types";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
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
      payload?.message ??
        validationMessage ??
        "The request could not be completed.",
      response.status,
      {
        errorId: payload?.error_id,
        code: payload?.code,
        details: payload?.details,
        requestId: payload?.request_id,
      },
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function icsRequest<T>(
  path: string,
  file: File,
  query: URLSearchParams,
): Promise<T> {
  const response = await fetch(`/api/v1${path}?${query.toString()}`, {
    method: "POST",
    headers: { "Content-Type": file.type || "text/calendar" },
    body: file,
  });
  return parseResponse<T>(response);
}

export const calendarApi = {
  listCalendars(signal?: AbortSignal) {
    return request<CalendarModel[]>("/calendars", { signal });
  },

  createDefaultCalendar() {
    return request<CalendarModel>("/calendars", {
      method: "POST",
      body: JSON.stringify({
        name: "Personal",
        description: "My personal calendar",
        color: "#d6a93a",
      }),
    });
  },

  createCalendar(payload: CalendarMutation) {
    return request<CalendarModel>("/calendars", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateCalendar(calendarId: string, payload: Partial<CalendarMutation>) {
    return request<CalendarModel>(`/calendars/${calendarId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  deleteCalendar(calendarId: string) {
    return request<void>(`/calendars/${calendarId}`, { method: "DELETE" });
  },

  updateCalendarVisibility(calendarId: string, isVisible: boolean) {
    return request<CalendarModel>(`/calendars/${calendarId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_visible: isVisible }),
    });
  },

  listEvents(
    startsBefore: Date,
    endsAfter: Date,
    options?: {
      calendarId?: string;
      search?: string;
      signal?: AbortSignal;
    },
  ) {
    const query = new URLSearchParams({
      starts_before: startsBefore.toISOString(),
      ends_after: endsAfter.toISOString(),
    });
    if (options?.calendarId) {
      query.set("calendar_id", options.calendarId);
    }
    if (options?.search) {
      query.set("search", options.search);
    }
    return request<CalendarEvent[]>(`/events?${query.toString()}`, {
      signal: options?.signal,
    });
  },

  createEvent(payload: EventMutation) {
    return request<CalendarEvent>("/events", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateEvent(eventId: string, payload: EventUpdateMutation) {
    return request<CalendarEvent>(`/events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  updateEventOccurrence(
    seriesId: string,
    occurrenceStartAt: string,
    payload: EventUpdateMutation,
  ) {
    const query = new URLSearchParams({
      recurrence_scope: "occurrence",
      occurrence_start_at: occurrenceStartAt,
    });
    return request<CalendarEvent>(`/events/${seriesId}?${query.toString()}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  updateEventSeries(seriesId: string, payload: EventUpdateMutation) {
    return request<CalendarEvent>(
      `/events/${seriesId}?recurrence_scope=series`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
    );
  },

  deleteEvent(eventId: string) {
    return request<void>(`/events/${eventId}`, { method: "DELETE" });
  },

  deleteEventOccurrence(seriesId: string, occurrenceStartAt: string) {
    const query = new URLSearchParams({
      recurrence_scope: "occurrence",
      occurrence_start_at: occurrenceStartAt,
    });
    return request<void>(`/events/${seriesId}?${query.toString()}`, {
      method: "DELETE",
    });
  },

  deleteEventSeries(seriesId: string) {
    return request<void>(`/events/${seriesId}?recurrence_scope=series`, {
      method: "DELETE",
    });
  },

  previewIcs(file: File) {
    return icsRequest<IcsPreview>(
      "/calendar-imports/ics/preview",
      file,
      new URLSearchParams({ file_name: file.name }),
    );
  },

  importIcs(file: File, options: IcsImportOptions) {
    const query = new URLSearchParams({
      file_name: file.name,
      calendar_color: options.calendarColor,
    });
    if (options.destinationCalendarId) {
      query.set("destination_calendar_id", options.destinationCalendarId);
    } else {
      query.set("calendar_name", options.calendarName);
    }
    return icsRequest<IcsImportResult>("/calendar-imports/ics", file, query);
  },

  previewIcsSubscription(url: string) {
    return request<IcsPreview>("/calendar-subscriptions/ics/preview", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
  },

  createIcsSubscription(options: IcsSubscriptionOptions) {
    return request<IcsImportResult>("/calendar-subscriptions/ics", {
      method: "POST",
      body: JSON.stringify({
        url: options.url,
        calendar_name: options.calendarName,
        calendar_color: options.calendarColor,
      }),
    });
  },
};
