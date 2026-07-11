import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "@/components/dashboard";
import { DashboardApp } from "@/components/dashboard-app";
import { PositionsPageApp } from "@/components/positions-page";
import {
  connectSession,
  disconnectSession,
  getCurrentMacro,
  getPortfolioPositions,
  getRealDashboard,
  getSessionStatus,
  selectAccount
} from "@/lib/api";
import type { CurrentMacroResponse, DashboardData, PortfolioPositionsResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  connectSession: vi.fn(),
  disconnectSession: vi.fn(),
  getCurrentMacro: vi.fn(),
  getPortfolioPositions: vi.fn(),
  getRealDashboard: vi.fn(),
  getSessionStatus: vi.fn(),
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

const portfolioPositions: PortfolioPositionsResponse = {
  schema_version: "1.0",
  report_type: "portfolio_positions",
  generated_at: "2026-07-09T12:00:00Z",
  as_of: "2026-07-09",
  account_label: "Весь портфель",
  positions: [
    {
      instrument_uid: "bond-1",
      ticker: "BOND",
      instrument_type: "INSTRUMENT_TYPE_BOND",
      instrument_name: "Bond A",
      isin: "RU000BOND",
      quantity: "2",
      average_position_price: { amount: "100.00", currency: "RUB" },
      current_price: { amount: "105.00", currency: "RUB" },
      market_value: { amount: "210.00", currency: "RUB" },
      source_status: "actual"
    },
    {
      instrument_uid: "share-1",
      ticker: "SHARE",
      instrument_type: "INSTRUMENT_TYPE_SHARE",
      instrument_name: "Share A",
      isin: "RU000SHARE",
      quantity: "3",
      average_position_price: { amount: "10.00", currency: "RUB" },
      current_price: null,
      market_value: null,
      source_status: "actual"
    }
  ],
  warnings: []
};

const currentMacro: CurrentMacroResponse = {
  schema_version: "1.0",
  report_type: "current_macro_indicators",
  generated_at: "2026-07-10T14:00:00Z",
  status: "fresh",
  key_rate: {
    value_percent: "14.25",
    effective_date: "2026-07-10",
    effective_from: null,
    source: "bank_of_russia",
    source_url: "https://www.cbr.ru/hd_base/keyrate/",
    fetched_at: "2026-07-10T14:00:00Z",
    quality_status: "actual"
  },
  ruonia: {
    value_percent: "14.43",
    rate_date: "2026-07-09",
    publication_date: "2026-07-10",
    volume_rub_billion: "673.42",
    trades_count: 61,
    participants_count: 20,
    calculation_status: null,
    source: "bank_of_russia",
    source_url: "https://www.cbr.ru/hd_base/ruonia/dynamics/",
    fetched_at: "2026-07-10T14:00:00Z",
    quality_status: "actual"
  },
  annual_inflation: {
    value_percent_yoy: "5.31",
    period: "2026-05",
    target_percent: "4.00",
    source: "rosstat_via_bank_of_russia",
    source_url: "https://www.cbr.ru/hd_base/infl/",
    fetched_at: "2026-07-10T14:00:00Z",
    quality_status: "actual"
  },
  warnings: [
    "RUONIA is published with a lag relative to the current date.",
    "Annual inflation is the latest published monthly year-on-year value, not a daily indicator."
  ]
};

describe("DashboardApp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCurrentMacro).mockResolvedValue(currentMacro);
    window.history.replaceState(null, "", "/");
  });

  it("clears submitted token from the form state and loads real dashboard", async () => {
    vi.mocked(getSessionStatus).mockResolvedValue({
      session: {
        status: "missing",
        expires_at: null,
        selected_account: null
      },
      accounts: []
    });
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

    await screen.findByText("Нет активной сессии. Подключите read-only token, чтобы увидеть реальные данные.");
    const input = screen.getByLabelText("T-Invest token") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "test-read-only-token" } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);

    await waitFor(() => expect(input.value).toBe(""));
    await waitFor(() => expect(connectSession).toHaveBeenCalledWith("test-read-only-token"));
    await waitFor(() => expect(getRealDashboard).toHaveBeenCalled());
  });

  it("refreshes real dashboard without reconnecting or dropping accounts", async () => {
    vi.mocked(getSessionStatus).mockResolvedValue({
      session: {
        status: "missing",
        expires_at: null,
        selected_account: null
      },
      accounts: []
    });
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

  it("selects connected accounts from a dropdown", async () => {
    vi.mocked(getSessionStatus).mockResolvedValue({
      session: {
        status: "missing",
        expires_at: null,
        selected_account: null
      },
      accounts: []
    });
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
        },
        {
          ref: "account_2",
          name: "IIS",
          type: "iis",
          status: "open",
          masked_id: "****5678",
          selected: false
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
    vi.mocked(selectAccount).mockResolvedValue({
      accounts: [
        {
          ref: "account_1",
          name: "Main",
          type: "brokerage",
          status: "open",
          masked_id: "****1234",
          selected: false
        },
        {
          ref: "account_2",
          name: "IIS",
          type: "iis",
          status: "open",
          masked_id: "****5678",
          selected: true
        }
      ]
    });
    vi.mocked(disconnectSession).mockResolvedValue();

    render(<DashboardApp initialDashboard={demoDashboard} />);

    await screen.findByText("Нет активной сессии. Подключите read-only token, чтобы увидеть реальные данные.");
    const input = screen.getByLabelText("T-Invest token") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "test-read-only-token" } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);

    const selector = (await screen.findByLabelText("Счёт")) as HTMLSelectElement;
    selector.value = "account_2";
    fireEvent.change(selector);

    await waitFor(() => expect(selectAccount).toHaveBeenCalledWith("account_2"));
  });

  it("restores an existing backend session from cookie on mount", async () => {
    vi.mocked(getSessionStatus).mockResolvedValue({
      session: {
        status: "connected",
        expires_at: "2026-07-09T12:00:00Z",
        selected_account: {
          ref: "portfolio_all",
          name: "Весь портфель"
        }
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

    await waitFor(() => expect(getSessionStatus).toHaveBeenCalled());
    await waitFor(() => expect(getRealDashboard).toHaveBeenCalled());
    expect(connectSession).not.toHaveBeenCalled();
    expect(screen.getAllByText("Весь портфель").length).toBeGreaterThan(0);
  });

  it("loads CBR macro indicators and shows them on the dashboard", async () => {
    vi.mocked(getSessionStatus).mockResolvedValue({
      session: {
        status: "missing",
        expires_at: null,
        selected_account: null
      },
      accounts: []
    });
    vi.mocked(getRealDashboard).mockResolvedValue({
      ...demoDashboard,
      mode: "real"
    });
    vi.mocked(disconnectSession).mockResolvedValue();
    vi.mocked(selectAccount).mockResolvedValue({ accounts: [] });

    render(<DashboardApp initialDashboard={demoDashboard} />);

    await screen.findAllByText("14.25%");
    expect(screen.getAllByText("14.43%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("5.31%").length).toBeGreaterThan(0);
    expect(screen.getByText(/Период: 10\.07\.2026/)).toBeTruthy();
    expect(screen.getByText(/Ставка за: 09\.07\.2026/)).toBeTruthy();
    expect(screen.getByText(/Период: 05\.2026/)).toBeTruthy();
  });

  it("links to the full positions page from sidebar and positions card action", () => {
    render(<Dashboard dashboard={demoDashboard} />);

    expect(screen.getByRole("link", { name: "Позиции" }).getAttribute("href")).toBe("/positions");
    expect(screen.getByRole("link", { name: "Все позиции →" }).getAttribute("href")).toBe("/positions");
  });

  it("shows all positions and filters bonds and shares", async () => {
    vi.mocked(getPortfolioPositions).mockResolvedValue(portfolioPositions);

    render(<PositionsPageApp />);

    await screen.findByText("Bond A");
    expect(screen.getByText("Share A")).toBeTruthy();
    expect(screen.getAllByText("нет данных").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Облигации" }));
    expect(screen.getByText("Bond A")).toBeTruthy();
    expect(screen.queryByText("Share A")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Акции" }));
    expect(screen.getByText("Share A")).toBeTruthy();
    expect(screen.queryByText("Bond A")).toBeNull();
  });

  it("shows missing session reconnect state while keeping demo dashboard available", async () => {
    vi.mocked(getSessionStatus).mockResolvedValue({
      session: {
        status: "missing",
        expires_at: null,
        selected_account: null
      },
      accounts: []
    });
    vi.mocked(getRealDashboard).mockResolvedValue({
      ...demoDashboard,
      mode: "real"
    });
    vi.mocked(disconnectSession).mockResolvedValue();
    vi.mocked(selectAccount).mockResolvedValue({ accounts: [] });

    render(<DashboardApp initialDashboard={demoDashboard} />);

    await screen.findByText("Нет активной сессии. Подключите read-only token, чтобы увидеть реальные данные.");
    expect(getRealDashboard).not.toHaveBeenCalled();
    expect(screen.getAllByText("Demo").length).toBeGreaterThan(0);
    const tokenInput = screen.getByLabelText("T-Invest token");
    expect(tokenInput).toBeTruthy();
    expect(tokenInput.closest("header")).not.toBeNull();
    expect(tokenInput.closest("aside")).toBeNull();
  });

  it("shows expired session reconnect state while keeping demo dashboard available", async () => {
    vi.mocked(getSessionStatus).mockResolvedValue({
      session: {
        status: "expired",
        expires_at: null,
        selected_account: null
      },
      accounts: []
    });
    vi.mocked(getRealDashboard).mockResolvedValue({
      ...demoDashboard,
      mode: "real"
    });
    vi.mocked(disconnectSession).mockResolvedValue();
    vi.mocked(selectAccount).mockResolvedValue({ accounts: [] });

    render(<DashboardApp initialDashboard={demoDashboard} />);

    await screen.findByText("Сессия истекла. Подключите read-only token заново.");
    expect(getRealDashboard).not.toHaveBeenCalled();
    expect(screen.getAllByText("Demo").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("T-Invest token")).toBeTruthy();
  });

  it("shows reconnect state instead of generic refresh error when real session expires", async () => {
    vi.mocked(getSessionStatus)
      .mockResolvedValueOnce({
        session: {
          status: "missing",
          expires_at: null,
          selected_account: null
        },
        accounts: []
      })
      .mockResolvedValueOnce({
        session: {
          status: "expired",
          expires_at: null,
          selected_account: null
        },
        accounts: []
      });
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
          account_label: "Весь портфель"
        }
      })
      .mockRejectedValueOnce(new Error("session expired"));
    vi.mocked(disconnectSession).mockResolvedValue();
    vi.mocked(selectAccount).mockResolvedValue({ accounts: [] });

    render(<DashboardApp initialDashboard={demoDashboard} />);

    const input = screen.getByLabelText("T-Invest token") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "test-read-only-token" } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);

    await screen.findAllByText("Весь портфель");
    fireEvent.click(screen.getByLabelText("Обновить данные"));

    await screen.findByText("Сессия истекла. Подключите read-only token заново.");
    expect(screen.queryByText("Не удалось обновить данные.")).toBeNull();
    expect(screen.getAllByText("Demo").length).toBeGreaterThan(0);
    expect((screen.getByLabelText("T-Invest token") as HTMLInputElement).value).toBe("");
  });
});
