/**
 * Month-switch UI tests (AGENTS.md § TDD: required for month-switch behaviour).
 *
 * FRONTEND.md § 2 and BACKEND.md § 3.5: the frontend polls, offers the switch
 * once, and falls back to a "Switch to current month" button if the user
 * declines. Nothing here may mutate a record.
 */
import { fireEvent, screen, waitFor } from "@testing-library/preact";
import { describe, expect, it } from "vitest";

import {
  MonthSwitchDialog,
  MonthSwitchProvider,
  SwitchCta,
  useMonthSwitch,
} from "@/components/MonthSwitch";
import { renderWithProviders, stubApi } from "../helpers";

function Probe() {
  const monthSwitch = useMonthSwitch();
  return <p data-testid="working-month">{monthSwitch.workingMonth ?? "none"}</p>;
}

function renderSwitch() {
  return renderWithProviders(
    <MonthSwitchProvider enabled>
      <Probe />
      <MonthSwitchDialog />
      <SwitchCta />
    </MonthSwitchProvider>,
  );
}

const PENDING = {
  current_month: "2025-08",
  last_acknowledged_month: "2025-07",
  needs_switch: true,
  earliest_month: "2025-03",
};

const SWITCHED = {
  current_month: "2025-08",
  last_acknowledged_month: "2025-08",
  needs_switch: false,
  earliest_month: "2025-03",
};

describe("MonthSwitch", () => {
  it("exposes the working month, not the calendar month", async () => {
    stubApi([{ match: /\/current-month$/, data: PENDING }]);

    renderSwitch();

    await waitFor(() =>
      expect(screen.getByTestId("working-month").textContent).toBe("2025-07"),
    );
  });

  it("offers the switch when the calendar has moved on", async () => {
    stubApi([{ match: /\/current-month$/, data: PENDING }]);

    renderSwitch();

    await waitFor(() =>
      expect(screen.getByText("A new month started")).toBeTruthy(),
    );
    expect(screen.getByText("Switch to 2025-08")).toBeTruthy();
  });

  it("stays quiet when already on the current month", async () => {
    stubApi([{ match: /\/current-month$/, data: SWITCHED }]);

    renderSwitch();

    await waitFor(() =>
      expect(screen.getByTestId("working-month").textContent).toBe("2025-08"),
    );
    expect(screen.queryByText("A new month started")).toBeNull();
    expect(screen.queryByTestId("switch-cta")).toBeNull();
  });

  it("posts the acknowledgement and drops the dialog", async () => {
    const fetchMock = stubApi([
      { match: /\/current-month\/switch$/, method: "POST", data: SWITCHED },
      { match: /\/current-month$/, data: PENDING },
    ]);

    renderSwitch();
    await waitFor(() => expect(screen.getByText("A new month started")).toBeTruthy());

    fireEvent.click(screen.getByText("Switch to 2025-08"));

    await waitFor(() =>
      expect(screen.queryByText("A new month started")).toBeNull(),
    );
    const posted = fetchMock.mock.calls.find(([url, init]) =>
      String(url).endsWith("/current-month/switch") &&
      (init as RequestInit | undefined)?.method === "POST",
    );
    expect(posted).toBeTruthy();
  });

  it("swaps the dialog for the CTA when declined, and switches from there", async () => {
    const fetchMock = stubApi([
      { match: /\/current-month\/switch$/, method: "POST", data: SWITCHED },
      { match: /\/current-month$/, data: PENDING },
    ]);

    renderSwitch();
    await waitFor(() => expect(screen.getByText("A new month started")).toBeTruthy());

    fireEvent.click(screen.getByText("Stay on 2025-07"));

    expect(screen.queryByText("A new month started")).toBeNull();
    const cta = screen.getByTestId("switch-cta");
    expect(cta.textContent).toBe("Switch to current month");

    fireEvent.click(cta);

    await waitFor(() =>
      expect(screen.getByTestId("working-month").textContent).toBe("2025-08"),
    );
    expect(fetchMock).toHaveBeenCalled();
  });
});
