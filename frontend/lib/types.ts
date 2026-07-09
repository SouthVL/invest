export type Money = {
  amount: string;
  currency: string;
};

export type DashboardMode = "demo" | "real";

export type PositionPreview = {
  instrument_uid: string;
  ticker: string;
  instrument_type: string;
  instrument_name: string;
  quantity: string;
  current_price: Money | null;
  market_value: Money | null;
};

export type DashboardData = {
  schema_version: string;
  mode: DashboardMode;
  portfolio: {
    status: string;
    account_label: string;
    total_value: Money | null;
    daily_yield: null;
    expected_yield: null;
    updated_at: string;
    period: string;
  };
  allocation: Array<{
    type: string;
    value: Money;
    share_percent: string | null;
  }>;
  positions_preview: PositionPreview[];
  cashflow_summary: {
    period: {
      as_of: string;
      months: number;
    };
    updated_at: string;
    total: Money;
    actual_total: Money;
    estimated_total: Money;
    unknown_count: number;
  } | null;
  macro: {
    status: "fresh" | "stale" | "unavailable";
    key_rate: string | null;
    inflation_yoy: string | null;
    updated_at: string | null;
  };
  warnings: string[];
};

export type DemoDashboard = DashboardData;

export type ConnectedAccount = {
  ref: string;
  name: string;
  type: string;
  status: string;
  masked_id: string;
  selected: boolean;
};

export type ConnectResponse = {
  session: {
    status: "connected";
    expires_at: string;
  };
  accounts: ConnectedAccount[];
};

export type AccountsResponse = {
  accounts: ConnectedAccount[];
};
