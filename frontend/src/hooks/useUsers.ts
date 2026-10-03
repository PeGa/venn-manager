/**
 * User management hooks (API_SURFACE.md § 3.2). Admin only.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/preact-query";

import * as settingsApi from "@/api/settings";
import { STALE_TIME_MS, keys } from "@/api/queryKeys";

/** Every non-deleted user. */
export function useUsers(enabled: boolean) {
  return useQuery({
    queryKey: keys.users,
    queryFn: settingsApi.fetchUsers,
    staleTime: STALE_TIME_MS,
    enabled,
  });
}

function useInvalidateUsers() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: keys.users });
  };
}

/** Create a user. */
export function useCreateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: settingsApi.createUser,
    onSuccess: invalidate,
  });
}

/** Edit a user's real name, password or admin flag. */
export function useUpdateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: (input: {
      id: number;
      patch: { real_name?: string; password?: string; is_admin?: boolean };
    }) => settingsApi.updateUser(input.id, input.patch),
    onSuccess: invalidate,
  });
}

/**
 * Soft-delete a user.
 *
 * The session is invalidated too: deleting yourself is refused by the backend,
 * but deleting anyone else can end a session this browser does not own, and the
 * admin list must not keep showing them.
 */
export function useDeleteUser() {
  const client = useQueryClient();
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: settingsApi.deleteUser,
    onSuccess: () => {
      invalidate();
      void client.invalidateQueries({ queryKey: keys.session });
      void client.invalidateQueries({ queryKey: ["records"] });
    },
  });
}
