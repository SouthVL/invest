import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardApp } from "@/components/dashboard-app";
import { connectSession, disconnectSession, getAccounts, getRealDashboard, selectAccount } from "@/lib/api";
import type { DashboardData } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  connectSession: vi.fn(),
  disconnectSession: vi.fn(),
  getAccounts: vi.fn(),
  getRealDashboard: vi.fn(),
  selectAccount: vi.fn()
}));

const demoDashboard: DashboardData = {
  schema_version: "1.0",
  mode: "demo",
  portfolio: {
    status: "fresh",
    account_label: "demo_account",
    total_value: { amount: "17615.00", currency: "RUB" },
    daily_yield: null,
    expected_yield: null,
    updated_at: "2026-07-01T09:00:00Z",
    period: "2026-07-01"
  },
  allocation: [],
  positions_preview: [],
  cashflow_summary: null,
  macro: {
    status: "unavailable",
    key_rate: null,
    inflation_yoy: null,
    updated_at: null
  },
  warnings: []
};

describe("DashboardApp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clears submitted token from the form state and loads real dashboard", async () => {
    vi.mocked(getAccounts).mockRejectedValue(new Error("not connected"));
    vi.mocked(connectSession).mockResolvedValue({
      session: {
        status: "connected",
        expires_at: "2026-07-09T12:00:00Z"
      },
      accounts: [
        {
          ref: "account_1",
          name: "Main",
          type: "brokerage",
          status: "open",
          masked_id: "****1234",
          selected: true
        }
      ]
    });
    vi.mocked(getRealDashboard).mockResolvedValue({
      ...demoDashboard,
      mode: "real",
      portfolio: {
        ...demoDashboard.portfolio,
        account_label: "Main"
      }
    });
    vi.mocked(disconnectSession).mockResolvedValue();
    vi.mocked(selectAccount).mockResolvedValue({ accounts: [] });

    render(<DashboardApp initialDashboard={demoDashboard} />);

    const input = screen.getByLabelText("T-Invest token") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "test-read-only-token" } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);

    await waitFor(() => expect(input.value).toBe(""));
    await waitFor(() => expect(connectSession).toHaveBeenCalledWith("test-read-only-token"));
    await waitFor(() => expect(getRealDashboard).toHaveBeenCalled());
  });

  it("refreshes real dashboard without reconnecting or dropping accounts", async () => {
    vi.mocked(getAccounts).mockRejectedValue(new Error("not connected"));
    vi.mocked(connectSession).mockResolvedValue({
      session: {
        status: "connected",
        expires_at: "2026-07-09T12:00:00Z"
      },
      accounts: [
        {
          ref: "portfolio_all",
          name: "Весь портфель",
          type: "aggregate",
          status: "mixed",
          masked_id: "2 счета",
          selected: true
        }
      ]
    });
    vi.mocked(getRealDashboard)
      .mockResolvedValueOnce({
        ...demoDashboard,
        mode: "real",
        portfolio: {
          ...demoDashboard.portfolio,
          account_label: "Весь портфель",
          updated_at: "2026-07-09T12:00:00Z"
        }
      })
      .mockResolvedValueOnce({
        ...demoDashboard,
        mode: "real",
        portfolio: {
          ...demoDashboard.portfolio,
          account_label: "Весь портфель",
          updated_at: "2026-07-09T12:05:00Z"
        }
      });
    vi.mocked(disconnectSession).mockResolvedValue();
    vi.mocked(selectAccount).mockResolvedValue({ accounts: [] });

    render(<DashboardApp initialDashboard={demoDashboard} />);

    const input = screen.getByLabelText("T-Invest token") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "test-read-only-token" } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);

    await screen.findAllByText("Весь портфель");
    fireEvent.click(screen.getByLabelText("Обновить данные"));

    await waitFor(() => expect(getRealDashboard).toHaveBeenCalledTimes(2));
    expect(connectSession).toHaveBeenCalledTimes(1);
    expect(disconnectSession).not.toHaveBeenCalled();
    expect(screen.getAllByText("Весь портфель").length).toBeGreaterThan(0);
  });

  it("restores an existing backend session from cookie on mount", async () => {
    vi.mocked(getAccounts).mockResolvedValue({
      accounts: [
        {
          ref: "portfolio_all",
          name: "Весь портфель",
          type: "aggregate",
          status: "mixed",
          masked_id: "2 счета",
          selected: true
        }
      ]
    });
    vi.mocked(getRealDashboard).mockResolvedValue({
      ...demoDashboard,
      mode: "real",
      portfolio: {
        ...demoDashboard.portfolio,
        account_label: "Весь портфель"
      }
    });
    vi.mocked(disconnectSession).mockResolvedValue();
    vi.mocked(selectAccount).mockResolvedValue({ accounts: [] });

    render(<DashboardApp initialDashboard={demoDashboard} />);

    await waitFor(() => expect(getAccounts).toHaveBeenCalled());
    await waitFor(() => expect(getRealDashboard).toHaveBeenCalled());
    expect(connectSession).not.toHaveBeenCalled();
    expect(screen.getAllByText("Весь портфель").length).toBeGreaterThan(0);
  });
});
