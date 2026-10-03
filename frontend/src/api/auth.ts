/**
 * Auth endpoints — API_SURFACE.md § 1.
 *
 * The session lives in an HttpOnly cookie, so nothing here stores a token.
 */
import { request } from "./client";
import type { SessionPayload } from "@/types/api";

/** Sign in. Also the call that reports `must_change_password`. */
export function login(username: string, password: string) {
  return request<SessionPayload>("/api/v1/auth/login", {
    method: "POST",
    body: { username, password },
  });
}

/** Sign out. The backend invalidates the session server-side. */
export function logout() {
  return request<null>("/api/v1/auth/logout", { method: "POST" });
}

/** Re-validate the session on load. 401 means "show the login screen". */
export function fetchSession() {
  return request<SessionPayload>("/api/v1/auth/session");
}

/** Change the calling user's password. The only call allowed during a forced change. */
export function changePassword(currentPassword: string, newPassword: string) {
  return request<null>("/api/v1/auth/password", {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });
}
