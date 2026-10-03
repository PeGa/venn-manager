/** Activity rows: actor, sentence, time and section (FRONTEND.md § 7). */
import { useNavigate } from "@solidjs/router";
import { For, Show } from "solid-js";

import { activitySection, sentence } from "@/domain/activity";
import { activityTime } from "@/domain/dates";
import type { ActivityEntry, Member } from "@/domain/model";
import { Avatar } from "@/ui/components/basics";
import { SECTION_LABEL, targetKey, targetPath } from "@/ui/navigation";
import { useServices } from "@/ui/services";

export function ActivityList(props: {
  entries: ActivityEntry[];
  members: Member[];
  currencySign: string;
  timezone: string;
  today: string;
  compact?: boolean;
}) {
  const { t, language, highlight } = useServices();
  const navigate = useNavigate();
  const actor = (id: string) => props.members.find((member) => member.id === id);

  return (
    <ul class="mt-1.5 flex flex-col">
      <For each={props.entries} fallback={<li class="py-3 text-xs text-muted">{t("activity_empty")}</li>}>
        {(entry) => {
          const section = activitySection(entry);
          const key = targetKey(entry.target);
          const who = () => actor(entry.actorId);
          const body = () => (
            <>
              <Avatar initial={who()?.initial ?? "?"} color={who()?.color ?? "#ddd"} size={props.compact === true ? 28 : 30} />
              <span class="flex-1 leading-snug" classList={{ "text-[12.5px]": props.compact === true, "text-[13px]": props.compact !== true }}>
                <b>{who()?.realName ?? ""}</b> {sentence(language(), entry, props.currencySign)}
                <span class="block text-[11px] text-faint">
                  {activityTime(language(), entry.at, new Date(), props.timezone, props.today)} · {t(SECTION_LABEL[section])}
                </span>
              </span>
            </>
          );
          return (
            <li class="border-t border-hairline">
              <Show when={key} fallback={<div class="flex items-center gap-3 px-1.5 py-2.5">{body()}</div>}>
                {(target) => (
                  <button
                    type="button"
                    class="-mx-1.5 flex w-[calc(100%+12px)] items-center gap-3 rounded-control px-1.5 py-2.5 text-left hover:bg-hover"
                    onClick={() => {
                      navigate(targetPath(entry.target, section));
                      highlight(target());
                    }}
                  >
                    {body()}
                    <span aria-hidden="true" class="text-lg text-faint">
                      ›
                    </span>
                  </button>
                )}
              </Show>
            </li>
          );
        }}
      </For>
    </ul>
  );
}
