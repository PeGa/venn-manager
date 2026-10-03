/** Settings (FRONTEND.md § 5.7): household-wide; member accounts are admin-only. */
import { useQuery } from "@tanstack/solid-query";
import { Show } from "solid-js";

import { keys } from "@/adapters/queries";
import type { Budget, Member } from "@/domain/model";
import type { HouseholdChanges } from "@/ports/api";
import { Skeleton } from "@/ui/components/basics";
import { useNotice, useRefresh } from "@/ui/errors";
import { ConceptsCard } from "@/ui/screens/settings/ConceptsCard";
import { CurrencyCard } from "@/ui/screens/settings/Currency";
import { HouseholdCard } from "@/ui/screens/settings/HouseholdCard";
import { MembersCard } from "@/ui/screens/settings/MembersCard";
import { useServices } from "@/ui/services";

export function Settings() {
  const { api, narrow } = useServices();
  const session = useQuery(() => ({ queryKey: keys.session, queryFn: () => api.session() }));
  const household = useQuery(() => ({ queryKey: keys.household, queryFn: () => api.household() }));
  const budgets = useQuery(() => ({ queryKey: keys.budgets, queryFn: () => api.budgets() }));
  const notice = useNotice();
  const refresh = useRefresh();

  const run = (call: Promise<unknown>) => void call.then(refresh).catch(notice.report);
  const saveHousehold = (changes: HouseholdChanges) => run(api.updateHousehold(changes));
  const removeMember = (member: Member) => run(api.removeMember(member.id));
  const addBudget = (name: string) => api.createBudget(name).then(refresh).then(() => undefined);
  const renameBudget = (budget: Budget, name: string) => run(api.updateBudget(budget.id, { name }));
  const removeBudget = (budget: Budget) => run(api.deleteBudget(budget.id));

  const ready = () => {
    const [h, s, b] = [household.data, session.data, budgets.data];
    return h && s && b ? { household: h, me: s.member, budgets: b.items } : undefined;
  };

  return (
    <Show when={ready()} fallback={<Skeleton lines={5} />}>
      {(data) => (
      <div class="flex flex-col gap-4">
        {notice.view()}
        <div class="grid items-start gap-4" classList={{ "grid-cols-[1fr_1.2fr_1fr]": !narrow(), "grid-cols-1 gap-2.5": narrow() }}>
          <div class="flex flex-col gap-4" classList={{ "gap-2.5": narrow() }}>
            <CurrencyCard household={data().household} save={(sign) => saveHousehold({ currencySign: sign })} />
            <HouseholdCard household={data().household} save={saveHousehold} />
          </div>
          <MembersCard household={data().household} me={data().me} remove={removeMember} />
          <ConceptsCard budgets={data().budgets} add={addBudget} rename={renameBudget} remove={removeBudget} />
        </div>
      </div>
      )}
    </Show>
  );
}
