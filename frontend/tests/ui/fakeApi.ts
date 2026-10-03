/**
 * An in-memory `Api` for screen tests. It keeps a small household in memory,
 * applies mutations to it, and records every call.
 */
import { vi } from "vitest";

import { figures } from "@/domain/budgets";
import type {
  ActivityEntry,
  Budget,
  Household,
  Member,
  Overview,
  Period,
  Session,
  Transaction,
} from "@/domain/model";
import { ApiError, type Api } from "@/ports/api";

export const PERIOD: Period = {
  month: "2026-09",
  start: "2026-09-01",
  end: "2026-09-30",
  today: "2026-09-28",
  daysInMonth: 30,
};

const ALEX: Member = {
  id: "m-alex",
  username: "alex",
  realName: "Alex",
  initial: "A",
  color: "#d9c7a8",
  role: "admin",
  status: "active",
  spentThisMonth: 8412,
};

const JORDAN: Member = {
  id: "m-jordan",
  username: "jordan",
  realName: "Jordan",
  initial: "J",
  color: "#a9c7b6",
  role: "member",
  status: "active",
  spentThisMonth: 0,
};

function budget(id: string, name: string, amount: number, actual: number, goal = false): Budget {
  return {
    id,
    name,
    amount,
    schedule: null,
    goal,
    createdAt: "2026-09-01T10:00:00Z",
    ...figures(amount, actual),
  };
}

function transaction(id: string, payee: string, b: Budget, amount: number, date: string, memberId = ALEX.id): Transaction {
  return {
    id,
    payee,
    budgetId: b.id,
    category: b.name,
    categoryDeleted: false,
    amount,
    memberId,
    date,
    createdAt: `${date}T10:00:00Z`,
    updatedAt: `${date}T10:00:00Z`,
    archived: false,
  };
}

export interface FakeState {
  session: Session | null;
  mustChangePassword: boolean;
  household: Household;
  budgets: Budget[];
  transactions: Transaction[];
  activity: ActivityEntry[];
  overview: Omit<Overview, "recentTransactions" | "activity" | "period" | "currencySign">;
}

export function seedState(): FakeState {
  const groceries = budget("b-groceries", "Groceries", -80000, -60400);
  const dining = budget("b-dining", "Dining out", -35000, -7040);
  const paycheck = budget("b-paycheck", "Paycheck", 224000, 224000);
  const trip = budget("b-trip", "Lisbon trip", -22000, -9600, true);
  return {
    session: {
      member: structuredClone(ALEX),
      mustChangePassword: false,
      preferences: { language: "en", theme: "light" },
    },
    mustChangePassword: false,
    household: {
      name: "Okafor-Lind",
      currencySign: "$",
      timezone: "UTC",
      openingBalance: 1290000,
      showMemberIncome: false,
      members: structuredClone([ALEX, JORDAN]),
    },
    budgets: [groceries, dining, paycheck, trip],
    transactions: [
      transaction("t-market", "Greenfield Market", groceries, -8412, "2026-09-28"),
      transaction("t-coffee", "Corner Coffee", dining, -640, "2026-09-28", JORDAN.id),
      transaction("t-pay", "Paycheck Northwind", paycheck, 224000, "2026-09-27", JORDAN.id),
      transaction("t-bistro", "Kiez Bistro", dining, -6400, "2026-09-27"),
    ],
    activity: [
      {
        id: "a1",
        actorId: JORDAN.id,
        action: "budget.amount",
        params: { name: "Dining out", amount: -35000 },
        at: "2026-09-27T09:00:00Z",
        target: { type: "budget", id: dining.id, goal: false },
      },
      {
        id: "a2",
        actorId: ALEX.id,
        action: "tx.create",
        params: { payee: "Greenfield Market" },
        at: "2026-09-28T09:58:00Z",
        target: { type: "transaction", id: "t-market", archived: false, month: "2026-09" },
      },
    ],
    overview: {
      budgetTotals: { limit: 115000, spent: 67440, leftToSpend: 47560, spentPct: 58.64 },
      forecast: { startCash: 1290000, planned: -28520, transactionsNet: 208548, transactionCount: 4, total: 1470028 },
      upcoming: [
        {
          budgetId: "b-rent",
          name: "Rent",
          dueDate: "2026-09-30",
          amount: -215000,
          actual: 0,
          soon: true,
          overdue: false,
        },
      ],
    },
  };
}

type Spied<T> = { [K in keyof T]: T[K] & ReturnType<typeof vi.fn> };

/** A fresh fake with its state, every method a spy. */
export function createFakeApi(state: FakeState = seedState()): { api: Spied<Api>; state: FakeState } {
  const ok = <T,>(value: T) => Promise.resolve(structuredClone(value));
  const recompute = (b: Budget) => {
    const actual = state.transactions
      .filter((t) => t.budgetId === b.id)
      .reduce((sum, t) => sum + t.amount, 0);
    Object.assign(b, figures(b.amount, actual));
  };
  const api: Api = {
    login: (username, password) => {
      if (password !== "right-password") {
        return Promise.reject(new ApiError(401, "UNAUTHORIZED", "Invalid username or password"));
      }
      state.session = { ...seedState().session!, member: { ...ALEX, username } };
      state.session.mustChangePassword = state.mustChangePassword;
      return ok(state.session);
    },
    logout: () => {
      state.session = null;
      return Promise.resolve();
    },
    session: () => {
      if (state.session === null) return Promise.reject(new ApiError(401, "UNAUTHORIZED", ""));
      if (state.session.mustChangePassword) {
        return Promise.reject(new ApiError(403, "PASSWORD_CHANGE_REQUIRED", ""));
      }
      return ok(state.session);
    },
    changePassword: (current) => {
      if (current !== "right-password") {
        return Promise.reject(new ApiError(400, "VALIDATION", "", "currentPassword"));
      }
      if (state.session !== null) state.session.mustChangePassword = false;
      return Promise.resolve();
    },
    updateMe: (changes) => {
      const session = state.session!;
      if (changes.realName !== undefined) session.member.realName = changes.realName;
      if (changes.username !== undefined) session.member.username = changes.username;
      if (changes.language !== undefined) session.preferences.language = changes.language;
      if (changes.theme !== undefined) session.preferences.theme = changes.theme;
      return ok(session);
    },
    household: () => ok(state.household),
    updateHousehold: (changes) => {
      Object.assign(state.household, changes);
      return ok(state.household);
    },
    createMember: (member) => {
      if (state.household.members.some((m) => m.username === member.username)) {
        return Promise.reject(new ApiError(409, "DUPLICATE_NAME", "", "username"));
      }
      const created: Member = {
        id: `m-${member.username}`,
        username: member.username,
        realName: member.realName,
        initial: member.realName.charAt(0).toUpperCase(),
        color: "#c9bfe0",
        role: member.isAdmin ? "admin" : "member",
        status: "active",
        spentThisMonth: 0,
      };
      state.household.members.push(created);
      return ok(created);
    },
    updateMember: (id, changes) => {
      const member = state.household.members.find((m) => m.id === id)!;
      if (changes.realName !== undefined) member.realName = changes.realName;
      if (changes.isAdmin !== undefined) member.role = changes.isAdmin ? "admin" : "member";
      return ok(member);
    },
    removeMember: (id) => {
      const member = state.household.members.find((m) => m.id === id)!;
      member.status = "removed";
      return Promise.resolve();
    },
    budgets: () => ok({ period: PERIOD, items: state.budgets }),
    createBudget: (name) => {
      if (state.budgets.some((b) => b.name.toLowerCase() === name.toLowerCase())) {
        return Promise.reject(new ApiError(409, "DUPLICATE_NAME", "", "name"));
      }
      const created = budget(`b-${name.toLowerCase()}`, name, 0, 0);
      state.budgets.push(created);
      return ok(created);
    },
    updateBudget: (id, changes) => {
      const target = state.budgets.find((b) => b.id === id)!;
      if (changes.name !== undefined) target.name = changes.name;
      if (changes.amount !== undefined) target.amount = changes.amount;
      if (changes.goal !== undefined) target.goal = changes.goal;
      if (changes.schedule !== undefined) target.schedule = changes.schedule;
      recompute(target);
      return ok(target);
    },
    deleteBudget: (id) => {
      state.budgets = state.budgets.filter((b) => b.id !== id);
      for (const t of state.transactions) {
        if (t.budgetId === id) t.categoryDeleted = true;
      }
      return Promise.resolve();
    },
    transactions: () =>
      ok({ items: state.transactions, page: 1, size: 200, total: state.transactions.length }),
    createTransaction: (input) => {
      const b = state.budgets.find((x) => x.id === input.budgetId)!;
      const created = transaction(`t-${String(state.transactions.length + 1)}`, input.payee, b, input.amount, PERIOD.today);
      state.transactions.unshift(created);
      recompute(b);
      return ok(created);
    },
    updateTransaction: (id, changes) => {
      const target = state.transactions.find((t) => t.id === id)!;
      if (changes.payee !== undefined) target.payee = changes.payee;
      if (changes.amount !== undefined) target.amount = changes.amount;
      if (changes.budgetId !== undefined) {
        const b = state.budgets.find((x) => x.id === changes.budgetId)!;
        target.budgetId = b.id;
        target.category = b.name;
      }
      return ok(target);
    },
    deleteTransaction: (id) => {
      state.transactions = state.transactions.filter((t) => t.id !== id);
      return Promise.resolve();
    },
    bulkDeleteTransactions: (ids) => {
      state.transactions = state.transactions.filter((t) => !ids.includes(t.id));
      return ok({ deleted: ids, notFound: [] });
    },
    overview: () =>
      ok({
        ...state.overview,
        period: PERIOD,
        currencySign: state.household.currencySign,
        recentTransactions: state.transactions.slice(0, 4),
        activity: state.activity.slice(0, 5),
      }),
    upcoming: () => ok(state.overview.upcoming),
    activity: () => ok({ items: state.activity, page: 1, size: 50, total: state.activity.length }),
    balance: () =>
      ok({
        balance: 1498548,
        monthIn: 224000,
        monthOut: 15452,
        members: state.household.showMemberIncome
          ? [{ memberId: JORDAN.id, monthIn: 224000, allTimeIn: 448000 }]
          : null,
      }),
    historyMonths: (query = {}) => {
      const months = [
        { month: "2026-08", matchCount: 3, totalCount: 3, spent: 30040, earned: 224000 },
        { month: "2026-07", matchCount: 1, totalCount: 1, spent: 30175, earned: 0 },
      ];
      const filtered = query.q ? months.filter((m) => m.month === "2026-08").map((m) => ({ ...m, matchCount: 1 })) : months;
      return ok({ items: filtered, page: 1, size: 12, total: filtered.length });
    },
    historyTransactions: (month) => {
      const rows: Transaction[] =
        month === "2026-08"
          ? [
              { ...transaction("h-pay", "Paycheck Northwind", state.budgets[2]!, 224000, "2026-08-29", JORDAN.id), archived: true },
              { ...transaction("h-market", "Greenfield Market", state.budgets[0]!, -21240, "2026-08-24"), archived: true },
              { ...transaction("h-cinema", "Cinema", budget("b-old", "Old fun", 0, 0), -4200, "2026-08-15"), archived: true, categoryDeleted: true },
            ]
          : [{ ...transaction("h-july", "Greenfield Market", state.budgets[0]!, -30175, "2026-07-22"), archived: true }];
      return ok({ items: rows, page: 1, size: 200, total: rows.length });
    },
    historyBreakdown: (month) =>
      ok({
        month,
        spent: 30040,
        earned: 224000,
        slices: [
          { budgetId: "b-groceries", category: "Groceries", amount: 21240, pct: 71 },
          { budgetId: "b-dining", category: "Dining out", amount: 8800, pct: 29 },
        ],
      }),
    historyFacets: () =>
      ok({
        categories: [
          { budgetId: "b-groceries", name: "Groceries", deleted: false },
          { budgetId: "b-old", name: "Old fun", deleted: true },
        ],
        members: [ALEX, JORDAN],
      }),
  };
  for (const name of Object.keys(api) as (keyof Api)[]) {
    api[name] = vi.fn(api[name]) as never;
  }
  return { api: api as Spied<Api>, state };
}
