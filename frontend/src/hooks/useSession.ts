/**
 * Session hooks.
 *
 * The cookie is HttpOnly, so the client never holds a token: the only way to
 * know who is signed in is to ask, and TanStack Query caches that answer.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/preact-query";

import * as authApi from "@/api/auth";
import { STALE_TIME_MS, keys } from "@/api/queryKeys";
import type { SessionPayload } from "@/types/api";

/** The current session, or a 401 that means "show the login screen". */
export function useSession() {
  return useQuery({
    queryKey: keys.session,
    queryFn: authApi.fetchSession,
    staleTime: STALE_TIME_MS,
  });
}

/**
 * Sign in.
 *
 * The response is written straight into the session cache so the shell renders
 * without a second round trip.
 */
export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { username: string; password: string }) =>
      authApi.login(input.username, input.password),
    onSuccess: (result) => {
      client.setQueryData(keys.session, result);
      client.invalidateQueries({ queryKey: keys.settings });
      client.invalidateQueries({ queryKey: keys.monthState });
    },
  });
}

/**
 * Sign out and drop every cached query.
 *
 * Clearing the cache matters on a shared household machine: the next person to
 * sign in must not see the previous user's data flash past while it refetches.
 */
export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      client.clear();
    },
  });
}

/** Change the calling user's password; lifts a forced-change session. */
export function useChangePassword() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { currentPassword: string; newPassword: string }) =>
      authApi.changePassword(input.currentPassword, input.newPassword),
    onSuccess: () => {
      const cached = client.getQueryData<{ data: SessionPayload }>(keys.session);
      if (cached !== undefined) {
        client.setQueryData(keys.session, {
          ...cached,
          data: { ...cached.data, must_change_password: false },
        });
      }
      client.invalidateQueries({ queryKey: keys.session });
    },
  });
}
