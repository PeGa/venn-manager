/**
 * The `Api` port over `fetch` (API_SURFACE.md § 0).
 *
 * Same-origin requests carry the session cookie. Writes are JSON, which with
 * SameSite=Lax is the CSRF defence. Errors become `ApiError` with the
 * contract code; a failed connection becomes `NETWORK`.
 */
import { ApiError, type Api, type HistoryQuery, type PageQuery } from "@/ports/api";

const BASE = "/api/v1";
const REVISION_HEADER = "X-Ledger-Rev";

type Fetcher = (url: string, init?: RequestInit) => Promise<Response>;
type Method = "GET" | "POST" | "PATCH" | "DELETE";

export interface HttpApiOptions {
  fetcher?: Fetcher;
  /** Called with every `X-Ledger-Rev` seen, for the sync chip. */
  onRevision?: (revision: number) => void;
}

function query(params: PageQuery | HistoryQuery = {}): string {
  const search = new URLSearchParams();
  for (const [name, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(name, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

async function errorFrom(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { code?: unknown; message?: unknown; field?: unknown };
    if (typeof body.code === "string") {
      const field = typeof body.field === "string" ? body.field : undefined;
      const message = typeof body.message === "string" ? body.message : "";
      return new ApiError(response.status, body.code, message, field);
    }
  } catch {
    // Not a contract error body; fall through.
  }
  return new ApiError(response.status, "INTERNAL", "Unexpected response");
}

/** Build the HTTP adapter. */
export function createHttpApi({ fetcher = fetch.bind(globalThis), onRevision }: HttpApiOptions = {}): Api {
  async function call<T>(method: Method, path: string, body?: unknown): Promise<T> {
    const init: RequestInit = { method, credentials: "same-origin" };
    if (method === "POST" || method === "PATCH") {
      init.headers = { "Content-Type": "application/json" };
      if (body !== undefined) {
        init.body = JSON.stringify(body);
      }
    }
    let response: Response;
    try {
      response = await fetcher(`${BASE}${path}`, init);
    } catch {
      throw new ApiError(0, "NETWORK", "Network unavailable");
    }
    if (!response.ok) {
      throw await errorFrom(response);
    }
    const revision = response.headers.get(REVISION_HEADER);
    if (revision !== null && onRevision !== undefined) {
      onRevision(Number(revision));
    }
    return (response.status === 204 ? undefined : await response.json()) as T;
  }

  return {
    login: (username, password) => call("POST", "/auth/login", { username, password }),
    logout: () => call("POST", "/auth/logout"),
    session: () => call("GET", "/auth/session"),
    changePassword: (currentPassword, newPassword) =>
      call("POST", "/auth/password", { currentPassword, newPassword }),
    updateMe: (changes) => call("PATCH", "/me", changes),

    household: () => call("GET", "/household"),
    updateHousehold: (changes) => call("PATCH", "/household", changes),
    createMember: (member) => call("POST", "/members", member),
    updateMember: (id, changes) => call("PATCH", `/members/${id}`, changes),
    removeMember: (id) => call("DELETE", `/members/${id}`),

    budgets: () => call("GET", "/budgets"),
    createBudget: (name) => call("POST", "/budgets", { name }),
    updateBudget: (id, changes) => call("PATCH", `/budgets/${id}`, changes),
    deleteBudget: (id) => call("DELETE", `/budgets/${id}`),

    transactions: (page) => call("GET", `/transactions${query(page)}`),
    createTransaction: (transaction) => call("POST", "/transactions", transaction),
    updateTransaction: (id, changes) => call("PATCH", `/transactions/${id}`, changes),
    deleteTransaction: (id) => call("DELETE", `/transactions/${id}`),
    bulkDeleteTransactions: (ids) => call("POST", "/transactions/bulk-delete", { ids }),

    overview: () => call("GET", "/overview"),
    upcoming: () => call("GET", "/upcoming"),
    activity: (page) => call("GET", `/activity${query(page)}`),
    balance: () => call("GET", "/balance"),

    historyMonths: (filters) => call("GET", `/history/months${query(filters)}`),
    historyTransactions: (month, filters) =>
      call("GET", `/history/months/${month}/transactions${query(filters)}`),
    historyBreakdown: (month, filters) =>
      call("GET", `/history/months/${month}/breakdown${query(filters)}`),
    historyFacets: () => call("GET", "/history/facets"),
  };
}
