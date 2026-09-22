/** Settings hook. Fetches global + per-user settings via tanstack-query. */
import { useQuery } from "@tanstack/preact-query";
import { getSettings } from "../api/client.ts";

export const useSettings = () => {
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
    staleTime: 300_000,
  });

  return { settings: data, isLoading };
};
