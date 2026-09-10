import { describe, expect, it } from "vitest";

import { ApiError, parseApiResponse } from "./api";

describe("Platform API response parsing", () => {
  it("preserves the safe error envelope for feature clients", async () => {
    const response = new Response(
      JSON.stringify({
        error_id: "error-1",
        code: "calendar_read_only",
        message: "This calendar is read-only.",
        details: { calendar_id: "calendar-1" },
        request_id: "request-1",
      }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    );

    const error = await parseApiResponse(response).catch(
      (reason: unknown) => reason,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      message: "This calendar is read-only.",
      status: 409,
      errorId: "error-1",
      code: "calendar_read_only",
      details: { calendar_id: "calendar-1" },
      requestId: "request-1",
    });
  });

  it("retains validation and non-JSON fallback messages", async () => {
    await expect(
      parseApiResponse(
        new Response(JSON.stringify({ detail: [{ msg: "Invalid date" }] }), {
          status: 422,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    ).rejects.toMatchObject({ message: "Invalid date", status: 422 });

    await expect(
      parseApiResponse(new Response("unavailable", { status: 503 }), "Retry"),
    ).rejects.toMatchObject({ message: "Retry", status: 503 });
  });

  it("supports successful JSON and empty responses", async () => {
    await expect(
      parseApiResponse<{ ok: boolean }>(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      ),
    ).resolves.toEqual({ ok: true });
    await expect(
      parseApiResponse<void>(new Response(null, { status: 204 })),
    ).resolves.toBeUndefined();
  });
});
