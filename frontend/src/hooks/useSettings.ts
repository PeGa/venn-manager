/**
 * Settings hooks (API_SURFACE.md § 3.1).
 *
 * `enabled` is driven by the session: asking for settings while signed out only
 * produces a 401, and the login screen falls back to the browser language.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/preact-query";

import * as settingsApi from "@/api/settings";
import type { SettingsPatch } from "@/api/settings";
import { STALE_TIME_MS, keys } from "@/api/queryKeys";
import type { ApiResult } from "@/api/client";
import type { Settings } from "@/types/api";

/** The caller's merged settings: currency, language, theme, working month, profile. */
export function useSettings(enabled: boolean) {
  return useQuery({
    queryKey: keys.settings,
    queryFn: settingsApi.fetchSettings,
    staleTime: STALE_TIME_MS,
    enabled,
  });
}

/**
 * Update settings.
 *
 * The response echoes only the changed keys, so the cache is patched rather than
 * dropped — a currency change must not throw away the working month and force a
 * re-read of every screen.
 */
export function useUpdateSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (patch: SettingsPatch) => settingsApi.patchSettings(patch),
    onSuccess: (result) => {
      const cached = client.getQueryData<ApiResult<Settings>>(keys.settings);
      if (cached !== undefined) {
        client.setQueryData<ApiResult<Settings>>(keys.settings, {
          ...cached,
          data: { ...cached.data, ...result.data },
        });
      }
      client.invalidateQueries({ queryKey: keys.settings });
    },
  });
}
