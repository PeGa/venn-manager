/** Members: everyone sees them, admins manage them (FRONTEND.md § 5.7). */
import { createSignal, For, Show } from "solid-js";

import type { Household, Member } from "@/domain/model";
import { formatMoney } from "@/domain/money";
import { Avatar, Button } from "@/ui/components/basics";
import { ConfirmDialog } from "@/ui/components/ConfirmDialog";
import { Highlight } from "@/ui/components/Highlight";
import { AccountDialog, InviteDialog } from "@/ui/screens/settings/MemberDialogs";
import { SettingsCard } from "@/ui/screens/settings/SettingsCard";
import { useServices } from "@/ui/services";

export function MembersCard(props: {
  household: Household;
  me: Member;
  remove: (member: Member) => void;
}) {
  const { t } = useServices();
  const [invite, setInvite] = createSignal("");
  const [inviting, setInviting] = createSignal<string | null>(null);
  const [editing, setEditing] = createSignal<Member | null>(null);
  const [removing, setRemoving] = createSignal<Member | null>(null);
  const isAdmin = () => props.me.role === "admin";
  const active = () => props.household.members.filter((member) => member.status === "active");
  const role = (member: Member) => t(member.role === "admin" ? "role_admin" : "role_member");
  const spent = (member: Member) =>
    formatMoney(member.spentThisMonth, props.household.currencySign, { decimals: 0 });

  const row = (member: Member) => (
    <>
      <Avatar initial={member.initial} color={member.color} />
      <span class="flex-1 text-left text-sm">
        <b>{member.realName}</b>
        <span class="block text-[11px] text-muted">
          {role(member)} · {t("member_spent", { amount: spent(member) })}
        </span>
      </span>
    </>
  );

  return (
    <SettingsCard section="members" title={t("members_title")} subtitle={t("members_subtitle")}>
      <ul>
        <For each={active()}>
          {(member) => (
            <li class="border-t border-hairline">
              <Highlight key={`member:${member.id}`} class="-mx-2 flex items-center gap-2.5 rounded-control px-2 py-2">
                <Show when={isAdmin()} fallback={<div class="flex flex-1 items-center gap-2.5">{row(member)}</div>}>
                  <button
                    type="button"
                    aria-label={t("member_edit", { name: member.realName })}
                    class="flex flex-1 items-center gap-2.5"
                    onClick={() => setEditing(member)}
                  >
                    {row(member)}
                  </button>
                  <Show when={member.id !== props.me.id}>
                    <Button kind="danger" small aria-label={t("member_remove", { name: member.realName })} onClick={() => setRemoving(member)}>
                      {t("action_remove")}
                    </Button>
                  </Show>
                </Show>
              </Highlight>
            </li>
          )}
        </For>
      </ul>
      <Show when={isAdmin()}>
        <form
          class="mt-2.5 flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            setInviting(invite().trim());
          }}
        >
          <input
            aria-label={t("invite_placeholder")}
            placeholder={t("invite_placeholder")}
            value={invite()}
            onInput={(event) => setInvite(event.currentTarget.value)}
            class="min-w-0 flex-1 rounded-control border border-input-border bg-input-bg px-3 py-2 text-[13px]"
          />
          <Button kind="primary" type="submit" small>
            {t("action_invite")}
          </Button>
        </form>
      </Show>
      <Show when={inviting()}>
        {(name) => (
          <InviteDialog
            name={name()}
            onClose={() => {
              setInviting(null);
              setInvite("");
            }}
          />
        )}
      </Show>
      <Show when={editing()}>{(member) => <AccountDialog member={member()} onClose={() => setEditing(null)} />}</Show>
      <Show when={removing()}>
        {(member) => (
          <ConfirmDialog
            title={t("member_remove_title", { name: member().realName })}
            body={t("member_remove_body")}
            confirmLabel={t("action_remove")}
            onClose={() => setRemoving(null)}
            onConfirm={() => {
              props.remove(member());
              setRemoving(null);
            }}
          />
        )}
      </Show>
    </SettingsCard>
  );
}
