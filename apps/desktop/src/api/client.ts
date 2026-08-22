export interface ProblemDetails {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  request_id?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly type?: string;
  readonly requestId?: string;
  readonly problem?: ProblemDetails;

  constructor(response: Response, problem?: ProblemDetails) {
    super(problem?.detail || problem?.title || `HTTP ${response.status}`);
    this.name = "ApiError";
    this.status = response.status;
    this.type = problem?.type;
    this.requestId = problem?.request_id || response.headers.get("x-request-id") || undefined;
    this.problem = problem;
  }
}

export class ApiTimeoutError extends Error {
  constructor(timeoutMs: number) {
    super(`request exceeded ${timeoutMs}ms timeout`);
    this.name = "ApiTimeoutError";
  }
}

export interface ApiClientOptions {
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
}

interface RequestOptions {
  signal?: AbortSignal;
  idempotencyKey?: string;
}

export interface ServerEvent<T = unknown> {
  id: number;
  event: string;
  data: T;
}

export interface StreamOptions<T> {
  signal: AbortSignal;
  onEvent: (event: ServerEvent<T>) => void;
  reconnects?: number;
  cursor?: number;
}

const RETRYABLE_STATUSES = new Set([502, 503, 504]);

export class ApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly retries: number;
  private readonly retryDelayMs: number;

  constructor(baseUrl: string, options: ApiClientOptions = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.timeoutMs = options.timeoutMs ?? 30_000;
    this.retries = options.retries ?? 2;
    this.retryDelayMs = options.retryDelayMs ?? 250;
  }

  get<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>("GET", path, undefined, options);
  }

  post<T>(path: string, body: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>("POST", path, body, options);
  }

  delete<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>("DELETE", path, undefined, options);
  }

  private async request<T>(
    method: string,
    path: string,
    body: unknown,
    options: RequestOptions,
  ): Promise<T> {
    const retryable = method === "GET" || method === "HEAD" || Boolean(options.idempotencyKey);
    const attempts = retryable ? this.retries + 1 : 1;
    let lastError: unknown;

    for (let attempt = 0; attempt < attempts; attempt += 1) {
      const controller = new AbortController();
      const timeoutError = new ApiTimeoutError(this.timeoutMs);
      const timer = setTimeout(() => controller.abort(timeoutError), this.timeoutMs);
      const externalAbort = () => controller.abort(options.signal?.reason);
      options.signal?.addEventListener("abort", externalAbort, { once: true });
      try {
        const headers = new Headers({ Accept: "application/json" });
        if (body !== undefined) headers.set("Content-Type", "application/json");
        if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);
        const response = await fetch(`${this.baseUrl}${path}`, {
          method,
          headers,
          body: body === undefined ? undefined : JSON.stringify(body),
          signal: controller.signal,
        });
        if (!response.ok) {
          if (retryable && RETRYABLE_STATUSES.has(response.status) && attempt + 1 < attempts) {
            await this.delay();
            continue;
          }
          throw await this.toApiError(response);
        }
        if (response.status === 204) return undefined as T;
        return (await response.json()) as T;
      } catch (error) {
        lastError = error;
        if (controller.signal.reason instanceof ApiTimeoutError) throw controller.signal.reason;
        if (options.signal?.aborted) throw options.signal.reason;
        if (error instanceof ApiError || !retryable || attempt + 1 >= attempts) throw error;
        await this.delay();
      } finally {
        clearTimeout(timer);
        options.signal?.removeEventListener("abort", externalAbort);
      }
    }
    throw lastError;
  }

  async stream<T = unknown>(path: string, options: StreamOptions<T>): Promise<void> {
    let cursor = options.cursor ?? 0;
    const reconnects = options.reconnects ?? Number.POSITIVE_INFINITY;
    for (let connection = 0; connection <= reconnects && !options.signal.aborted; connection += 1) {
      try {
        const headers = new Headers({ Accept: "text/event-stream" });
        if (cursor > 0) headers.set("Last-Event-ID", String(cursor));
        const response = await fetch(`${this.baseUrl}${path}`, {
          headers,
          signal: options.signal,
        });
        if (!response.ok) throw await this.toApiError(response);
        if (!response.body) throw new Error("SSE response has no body");
        const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = "";
        while (!options.signal.aborted) {
          const { done, value } = await reader.read();
          buffer = (buffer + (value ?? "")).replaceAll("\r\n", "\n");
          let boundary = buffer.indexOf("\n\n");
          while (boundary >= 0) {
            const frame = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);
            const event = parseServerEvent<T>(frame);
            if (event) {
              cursor = event.id;
              options.onEvent(event);
            }
            boundary = buffer.indexOf("\n\n");
          }
          if (done) break;
        }
      } catch (error) {
        if (options.signal.aborted) return;
        if (error instanceof ApiError && !RETRYABLE_STATUSES.has(error.status)) throw error;
        if (connection >= reconnects) throw error;
      }
      if (!options.signal.aborted && connection < reconnects) await this.delay();
    }
  }

  private async toApiError(response: Response): Promise<ApiError> {
    let problem: ProblemDetails | undefined;
    if (response.headers.get("content-type")?.includes("json")) {
      try {
        problem = (await response.json()) as ProblemDetails;
      } catch {
        problem = undefined;
      }
    }
    return new ApiError(response, problem);
  }

  private async delay(): Promise<void> {
    if (this.retryDelayMs === 0) return;
    await new Promise((resolve) => setTimeout(resolve, this.retryDelayMs));
  }
}

function parseServerEvent<T>(frame: string): ServerEvent<T> | null {
  if (!frame || frame.startsWith(":")) return null;
  let id = 0;
  let event = "message";
  const data: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("id:")) id = Number(line.slice(3).trim());
    else if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  const raw = data.join("\n");
  let parsed: unknown = raw;
  try {
    parsed = JSON.parse(raw);
  } catch {
    // Text event payloads are valid SSE.
  }
  return { id, event, data: parsed as T };
}
