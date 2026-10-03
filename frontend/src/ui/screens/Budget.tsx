/** Budget (FRONTEND.md § 5.2): every non-goal budget, then a link to add more. */
import { AddConceptLink, BudgetList } from "@/ui/screens/BudgetList";

export function BudgetScreen() {
  return <BudgetList goals={false} trailing={<AddConceptLink />} />;
}
