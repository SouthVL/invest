export type Money = {
  amount: string;
  currency: string;
};

export type DashboardMode = "demo" | "real";

export type PositionPreview = {
  instrument_uid: string;
  position_uid?: string;
  figi?: string;
  ticker: string;
  instrument_type: string;
  instrument_name: string;
  isin?: string;
  quantity: string;
  average_position_price?: Money | null;
  current_price: Money | null;
  market_value: Money | null;
  source_status?: string;
};

export type PortfolioPositionsResponse = {
  schema_version: string;
  report_type: "portfolio_positions";
  generated_at: string;
  as_of: string;
  account_label: string;
  positions: PositionPreview[];
  warnings: string[];
};

export type IncomeFilterType = "all" | "coupon" | "dividend";
export type IncomeFilterStatus = "all" | "confirmed" | "forecast";
export type IncomePeriod = "3m" | "6m" | "12m";

export type IncomePayment = {
  instrument_uid: string;
  instrument_name: string;
  figi: string | null;
  isin: string | null;
  payment_date: string;
  payment_month: string;
  income_type: "coupon" | "dividend";
  status: "confirmed" | "forecast";
  amount_per_unit: Money;
  payment_amount_per_unit: Money;
  quantity: string;
  total: Money;
  payment_total: Money;
  currency: string;
  source: string;
};

export type IncomeResponse = {
  schema_version: string;
  report_type: "income";
  generated_at: string;
  period: {
    label: IncomePeriod;
    from: string;
    to: string;
    months: number;
  };
  currency: string;
  filters: {
    type: IncomeFilterType;
    status: IncomeFilterStatus;
  };
  summary: {
    total: Money;
    coupons: Money;
    dividends: Money;
    confirmed: Money;
    forecast: Money;
    payments_count: number;
    nearest_payment: IncomePayment | null;
  };
  monthly: Array<{
    month: string;
    coupons: Money;
    dividends: Money;
    confirmed: Money;
    forecast: Money;
    total: Money;
  }>;
  payments: IncomePayment[];
  warnings: string[];
  data_quality: Record<string, unknown>;
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
    status: "fresh" | "partial" | "stale" | "unavailable";
    key_rate: string | null;
    key_rate_period?: string | null;
    key_rate_updated_at?: string | null;
    key_rate_quality?: string | null;
    ruonia?: string | null;
    ruonia_period?: string | null;
    ruonia_publication_date?: string | null;
    ruonia_updated_at?: string | null;
    ruonia_quality?: string | null;
    inflation_yoy: string | null;
    inflation_period?: string | null;
    inflation_updated_at?: string | null;
    inflation_quality?: string | null;
    updated_at: string | null;
  };
  warnings: string[];
};

export type CurrentMacroResponse = {
  schema_version: string;
  report_type: "current_macro_indicators";
  generated_at: string;
  status: "fresh" | "partial" | "unavailable";
  key_rate: {
    value_percent: string;
    effective_date: string;
    effective_from: string | null;
    source: string;
    source_url: string;
    fetched_at: string;
    quality_status: "actual" | "cached" | "stale" | "unavailable";
  } | null;
  ruonia: {
    value_percent: string;
    rate_date: string;
    publication_date: string;
    volume_rub_billion: string | null;
    trades_count: number | null;
    participants_count: number | null;
    calculation_status: string | null;
    source: string;
    source_url: string;
    fetched_at: string;
    quality_status: "actual" | "cached" | "stale" | "unavailable";
  } | null;
  annual_inflation: {
    value_percent_yoy: string;
    period: string;
    target_percent: string | null;
    source: string;
    source_url: string;
    fetched_at: string;
    quality_status: "actual" | "cached" | "stale" | "unavailable";
  } | null;
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

export type SessionStatusResponse = {
  session: {
    status: "connected" | "expired" | "missing";
    expires_at: string | null;
    selected_account: {
      ref: string;
      name: string;
    } | null;
  };
  accounts: ConnectedAccount[];
};
