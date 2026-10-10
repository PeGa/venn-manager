/**
 * The API port: everything the screens may ask of the backend
 * (API_SURFACE.md). Adapters implement it; screens never call `fetch`.
 */
import type {
  ActivityEntry,
  Balance,
  Breakdown,
  Budget,
  Cents,
  Household,
  HistoryFacets,
  HistoryMonth,
  IsoDate,
  Member,
  MonthKey,
  Overview,
  Page,
  Schedule,
  Session,
  Theme,
  Transaction,
  UpcomingItem,
  Uuid,
} from "@/domain/model";

/** A failed call. `code` is the contract error code, or `NETWORK`. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly field?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface PageQuery {
  page?: number;
  size?: number;
}

export interface HistoryQuery extends PageQuery {
  q?: string;
  memberId?: Uuid;
  budgetId?: Uuid;
}

export interface ProfileChanges {
  username?: string;
  realName?: string;
  language?: "en" | "es";
  theme?: Theme;
}

export interface HouseholdChanges {
  name?: string;
  currencySign?: string;
  timezone?: string;
  openingBalance?: Cents;
  showMemberIncome?: boolean;
}

export interface NewMember {
  username: string;
  realName: string;
  password: string;
  isAdmin: boolean;
}

export interface MemberChanges {
  realName?: string;
  password?: string;
  isAdmin?: boolean;
}

export interface BudgetChanges {
  name?: string;
  amount?: Cents;
  schedule?: Schedule | null;
  goal?: boolean;
}

export interface NewTransaction {
  budgetId: Uuid;
  amount: Cents;
  date?: IsoDate;
  memberId?: Uuid;
}

export type TransactionChanges = Partial<NewTransaction>;

export interface Api {
  login(username: string, password: string): Promise<Session>;
  logout(): Promise<void>;
  session(): Promise<Session>;
  changePassword(currentPassword: string, newPassword: string): Promise<void>;
  updateMe(changes: ProfileChanges): Promise<Session>;

  household(): Promise<Household>;
  updateHousehold(changes: HouseholdChanges): Promise<Household>;
  createMember(member: NewMember): Promise<Member>;
  updateMember(id: Uuid, changes: MemberChanges): Promise<Member>;
  removeMember(id: Uuid): Promise<void>;

  budgets(): Promise<{ period: Overview["period"]; items: Budget[] }>;
  createBudget(name: string): Promise<Budget>;
  updateBudget(id: Uuid, changes: BudgetChanges): Promise<Budget>;
  deleteBudget(id: Uuid): Promise<void>;

  transactions(query?: PageQuery): Promise<Page<Transaction>>;
  createTransaction(transaction: NewTransaction): Promise<Transaction>;
  updateTransaction(id: Uuid, changes: TransactionChanges): Promise<Transaction>;
  deleteTransaction(id: Uuid): Promise<void>;
  bulkDeleteTransactions(ids: Uuid[]): Promise<{ deleted: Uuid[]; notFound: Uuid[] }>;

  overview(): Promise<Overview>;
  upcoming(): Promise<UpcomingItem[]>;
  activity(query?: PageQuery): Promise<Page<ActivityEntry>>;
  balance(): Promise<Balance>;

  historyMonths(query?: HistoryQuery): Promise<Page<HistoryMonth>>;
  historyTransactions(month: MonthKey, query?: HistoryQuery): Promise<Page<Transaction>>;
  historyBreakdown(month: MonthKey, query?: HistoryQuery): Promise<Breakdown>;
  historyFacets(): Promise<HistoryFacets>;
}
