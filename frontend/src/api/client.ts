/**
 * The single place that talks HTTP to the backend.
 *
 * Every endpoint returns the same envelope (API_SURFACE.md § Response Envelope),
 * so this module unwraps it once and turns failures into typed errors.
 * Components never see a raw status code or a server message: they get an
 * `ErrorCode` and map it to a localised string.
 */
import type { TranslationKey } from "@/l10n";
import type { ErrorCode, Envelope, PageMeta } from "@/types/api";

/** The backend answered with a contract error. */
export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly status: number;

  constructor(code: ErrorCode, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/** The request never completed. Retried by TanStack Query, up to 3 attempts. */
export class NetworkError extends Error {
  constructor() {
    super("Network request failed");
    this.name = "NetworkError";
  }
}

export type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

/** Query values. `undefined`, `null` and blank strings are dropped. */
export type QueryParams = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  method?: HttpMethod;
  /** Serialised to JSON. Omit it entirely for a body-less request. */
  body?: unknown;
  query?: QueryParams;
}

export interface ApiResult<T> {
  data: T;
  meta: PageMeta | null;
}

const GENERIC_MESSAGE = "Request failed";

/**
 * Render query parameters, dropping absent and blank values.
 *
 * Zero and false are kept: `page=0` and `flag=false` are meaningful, while an
 * empty `search` would change what the backend filters on.
 */
export function buildQuery(params: QueryParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue;
    }
    if (typeof value === "string" && value.trim() === "") {
      continue;
    }
    search.append(key, String(value));
  }
  const encoded = search.toString();
  return encoded === "" ? "" : `?${encoded}`;
}

/**
 * Call an endpoint and unwrap the envelope.
 *
 * Throws {@link ApiError} for any contract error and {@link NetworkError} when
 * the request could not be made at all. Cookies carry the session, so requests
 * are same-origin — the Vite dev server proxies `/api` to the backend.
 */
export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiResult<T>> {
  const url = `${path}${options.query === undefined ? "" : buildQuery(options.query)}`;
  const hasBody = options.body !== undefined;

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        ...(hasBody ? { "Content-Type": "application/json" } : {}),
      },
      body: hasBody ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new NetworkError();
  }

  const envelope = await readEnvelope(response);
  if (envelope.error !== null) {
    throw new ApiError(envelope.error.code, envelope.error.message, response.status);
  }
  if (!response.ok) {
    throw new ApiError("INTERNAL_ERROR", GENERIC_MESSAGE, response.status);
  }
  return { data: envelope.data as T, meta: envelope.meta };
}

/**
 * Map a caught error onto the l10n key to show the user.
 *
 * AGENTS.md § Error Handling Patterns: raw codes and server messages are never
 * displayed. The server's message is kept on the error for the console, not for
 * the screen.
 */
export function errorKey(error: unknown): TranslationKey {
  if (error instanceof NetworkError) {
    return "error_network";
  }
  if (!(error instanceof ApiError)) {
    return "error_unknown";
  }
  switch (error.code) {
    case "UNAUTHORIZED":
      return "error_unauthorized";
    case "PASSWORD_CHANGE_REQUIRED":
      return "error_password_change_required";
    case "FORBIDDEN":
      return "error_forbidden";
    case "NOT_FOUND":
      return "error_not_found";
    case "CONFLICT":
      return "error_conflict";
    case "GONE":
      return "error_gone";
    case "VALIDATION_ERROR":
      return "error_validation";
    default:
      return "error_internal";
  }
}

/**
 * True when the failure is the force-password-change gate.
 *
 * `GET /auth/session` answers a restricted session with this code rather than a
 * payload, so the app cannot learn "signed in but restricted" any other way.
 */
export function isPasswordChangeRequired(error: unknown): boolean {
  return error instanceof ApiError && error.code === "PASSWORD_CHANGE_REQUIRED";
}

async function readEnvelope(response: Response): Promise<Envelope<unknown>> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("json")) {
    throw new ApiError("INTERNAL_ERROR", GENERIC_MESSAGE, response.status);
  }
  let parsed: unknown;
  try {
    parsed = await response.json();
  } catch {
    throw new ApiError("INTERNAL_ERROR", GENERIC_MESSAGE, response.status);
  }
  if (!isEnvelope(parsed)) {
    throw new ApiError("INTERNAL_ERROR", GENERIC_MESSAGE, response.status);
  }
  return parsed;
}

function isEnvelope(value: unknown): value is Envelope<unknown> {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return "data" in candidate && "error" in candidate;
}
