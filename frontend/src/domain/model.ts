/**
 * Core value types shared by the domain and the API port (API_SURFACE.md § 0).
 */

/** Integer cents, signed. `-8412` is −84.12. */
export type Cents = number;
/** `YYYY-MM-DD`, household-local. */
export type IsoDate = string;
/** ISO 8601 instant with offset. */
export type IsoDateTime = string;
/** `YYYY-MM`. */
export type MonthKey = string;
export type Uuid = string;

export type Repeat = "once" | "weekly" | "biweekly" | "monthly";

/** When a budget is due (API_SURFACE.md § 1.4). */
export interface Schedule {
  repeat: Repeat;
  anchor: IsoDate;
}

/** The current month in the household time zone (API_SURFACE.md § 1.1). */
export interface Period {
  month: MonthKey;
  start: IsoDate;
  end: IsoDate;
  today: IsoDate;
  daysInMonth: number;
}

export interface Member {
  id: Uuid;
  username: string;
  realName: string;
  initial: string;
  color: string;
  role: "admin" | "member";
  status: "active" | "removed";
  spentThisMonth: Cents;
}

export interface Household {
  name: string;
  currencySign: string;
  timezone: string;
  openingBalance: Cents;
  showMemberIncome: boolean;
  members: Member[];
}

export interface Budget {
  id: Uuid;
  name: string;
  amount: Cents;
  schedule: Schedule | null;
  goal: boolean;
  createdAt: IsoDateTime;
  actual: Cents;
  projected: Cents;
  remaining: Cents;
  over: boolean;
  overBy: Cents;
  progressPct: number;
}

export interface Transaction {
  id: Uuid;
  budgetId: Uuid;
  category: string;
  categoryDeleted: boolean;
  amount: Cents;
  memberId: Uuid;
  date: IsoDate;
  createdAt: IsoDateTime;
  updatedAt: IsoDateTime;
  archived: boolean;
}

export interface UpcomingItem {
  budgetId: Uuid;
  name: string;
  dueDate: IsoDate;
  amount: Cents;
  actual: Cents;
  soon: boolean;
  overdue: boolean;
}

export interface Forecast {
  startCash: Cents;
  planned: Cents;
  transactionsNet: Cents;
  transactionCount: number;
  total: Cents;
}

export type ActivityTarget =
  | { type: "transaction"; id: Uuid; archived: boolean; month: MonthKey }
  | { type: "budget"; id: Uuid; goal: boolean }
  | { type: "member"; id: Uuid }
  | { type: "settings"; section: "currency" | "household" | "members" | "budgets" }
  | { type: "none" };

export type ActivityAction =
  | "tx.create"
  | "tx.update"
  | "tx.delete"
  | "tx.bulkDelete"
  | "budget.create"
  | "budget.rename"
  | "budget.amount"
  | "budget.schedule"
  | "budget.goal"
  | "budget.delete"
  | "member.invite"
  | "member.update"
  | "member.remove"
  | "settings.currency"
  | "settings.name"
  | "settings.timezone"
  | "settings.openingBalance"
  | "settings.memberIncome";

export interface ActivityEntry {
  id: Uuid;
  actorId: Uuid;
  action: ActivityAction;
  params: Record<string, string | number | boolean>;
  at: IsoDateTime;
  target: ActivityTarget;
}

export interface Overview {
  period: Period;
  currencySign: string;
  forecast: Forecast;
  upcoming: UpcomingItem[];
  recentTransactions: Transaction[];
  activity: ActivityEntry[];
}

export interface HistoryMonth {
  month: MonthKey;
  matchCount: number;
  totalCount: number;
  spent: Cents;
  earned: Cents;
}

export interface Breakdown {
  month: MonthKey;
  spent: Cents;
  earned: Cents;
  slices: { budgetId: Uuid; category: string; amount: Cents; pct: number }[];
}

export interface HistoryFacets {
  categories: { budgetId: Uuid; name: string; deleted: boolean }[];
  members: Member[];
}

export interface Balance {
  balance: Cents;
  monthIn: Cents;
  monthOut: Cents;
  members: { memberId: Uuid; monthIn: Cents; allTimeIn: Cents }[] | null;
}

export type Theme = "light" | "dark" | "system";

export interface Session {
  member: Member;
  mustChangePassword: boolean;
  preferences: { language: "en" | "es" | null; theme: Theme };
}

export interface Page<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
}
