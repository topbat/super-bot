import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError } from "./client";

afterEach(() => vi.restoreAllMocks());

describe("ApiClient", () => {
  it("throws typed problem details with request id", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "https://super-bot.dev/problems/not-found",
          title: "Resource not found",
          status: 404,
          detail: "bot missing",
          request_id: "request-7",
        }),
        { status: 404, headers: { "content-type": "application/problem+json" } },
      ),
    );

    await expect(new ApiClient("http://api.test/api/v1").get("/bots/missing")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      requestId: "request-7",
      message: "bot missing",
    } satisfies Partial<ApiError>);
  });

  it("aborts requests at the configured timeout", async () => {
    vi.useFakeTimers();
    vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) =>
      new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(init.signal?.reason));
      }),
    );
    const pending = new ApiClient("http://api.test", { timeoutMs: 50 }).get("/slow");
    const timeoutAssertion = expect(pending).rejects.toMatchObject({ name: "ApiTimeoutError" });

    await vi.advanceTimersByTimeAsync(51);

    await timeoutAssertion;
    vi.useRealTimers();
  });

  it("retries safe GETs but not unkeyed writes", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));
    const client = new ApiClient("http://api.test", { retries: 2, retryDelayMs: 0 });

    await expect(client.get("/bots")).rejects.toThrow("offline");
    expect(fetchMock).toHaveBeenCalledTimes(3);

    fetchMock.mockClear();
    await expect(client.post("/bots", { name: "No retry" })).rejects.toThrow("offline");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("reconnects SSE with the last received event id", async () => {
    const first = new Response("id: 4\nevent: started\ndata: {\"step\":1}\n\n");
    const second = new Response("id: 5\nevent: completed\ndata: {}\n\n");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(first).mockResolvedValueOnce(second);
    const client = new ApiClient("http://api.test", { retryDelayMs: 0 });
    const controller = new AbortController();
    const events: number[] = [];

    await client.stream("/tasks/t1/events", {
      signal: controller.signal,
      reconnects: 1,
      onEvent(event) {
        events.push(event.id);
        if (event.id === 5) controller.abort();
      },
    });

    expect(events).toEqual([4, 5]);
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("Last-Event-ID")).toBe("4");
  });
});
