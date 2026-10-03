/**
 * Settings and user management — API_SURFACE.md § 3.1 and § 3.2.
 */
import { request } from "./client";
import type { Settings, UserSummary } from "@/types/api";

/** Fields a profile or preference update may carry. */
export type SettingsPatch = Partial<
  Pick<Settings, "currency" | "language" | "theme" | "username" | "real_name">
>;

/** Read the caller's merged settings. */
export function fetchSettings() {
  return request<Settings>("/api/v1/settings");
}

/**
 * Update settings. The backend picks the scope from the key, and `currency`
 * affects every user — the UI confirms that before calling this.
 */
export function patchSettings(patch: SettingsPatch) {
  return request<SettingsPatch>("/api/v1/settings", { method: "PATCH", body: patch });
}

/** List users. Admin only. */
export function fetchUsers() {
  return request<UserSummary[]>("/api/v1/settings/users");
}

/** Create a user. Admin only. */
export function createUser(input: {
  username: string;
  real_name: string;
  password: string;
  is_admin: boolean;
}) {
  return request<UserSummary>("/api/v1/settings/users", { method: "POST", body: input });
}

/** Edit a user's real name, password or admin flag. Admin only. */
export function updateUser(
  id: number,
  patch: { real_name?: string; password?: string; is_admin?: boolean },
) {
  return request<UserSummary>(`/api/v1/settings/users/${id}`, {
    method: "PATCH",
    body: patch,
  });
}

/** Soft-delete a user. Admin only; cannot target yourself or the last admin. */
export function deleteUser(id: number) {
  return request<null>(`/api/v1/settings/users/${id}`, { method: "DELETE" });
}
