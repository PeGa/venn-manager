/** Authentication hook. Manages session state via GET /api/auth/me. */
import { useQuery, useQueryClient } from "@tanstack/preact-query";
import { getMe, logout as logoutApi } from "../api/client.ts";
import type { User } from "../types/index.ts";

export const useAuth = () => {
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const { user } = await getMe();
      return user;
    },
    retry: false,
    staleTime: 60_000,
  });

  const logout = async () => {
    await logoutApi();
    queryClient.clear();
  };

  return {
    user: data as User | undefined,
    isLoading,
    logout,
    refetch,
  };
};
