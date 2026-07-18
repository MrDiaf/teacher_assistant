import type { CalendarEvent, CalendarModel, EventMutation } from "./types";

interface ApiErrorPayload {
  code?: string;
  message?: string;
  detail?: string | { msg?: string }[];
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
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
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
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

  updateCalendarVisibility(calendarId: string, isVisible: boolean) {
    return request<CalendarModel>(`/calendars/${calendarId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_visible: isVisible }),
    });
  },

  listEvents(startsBefore: Date, endsAfter: Date, signal?: AbortSignal) {
    const query = new URLSearchParams({
      starts_before: startsBefore.toISOString(),
      ends_after: endsAfter.toISOString(),
    });
    return request<CalendarEvent[]>(`/events?${query.toString()}`, { signal });
  },

  createEvent(payload: EventMutation) {
    return request<CalendarEvent>("/events", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateEvent(eventId: string, payload: EventMutation) {
    return request<CalendarEvent>(`/events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  deleteEvent(eventId: string) {
    return request<void>(`/events/${eventId}`, { method: "DELETE" });
  },
};
