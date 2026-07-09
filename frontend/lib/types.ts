export type Money = {
  amount: string;
  currency: string;
};

export type PositionPreview = {
  instrument_uid: string;
  ticker: string;
  instrument_type: string;
  instrument_name: string;
  quantity: string;
  current_price: Money | null;
  market_value: Money | null;
};

export type DemoDashboard = {
  schema_version: string;
  mode: "demo";
  portfolio: {
    status: string;
    account_label: string;
    total_value: Money;
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
  };
  macro: {
    status: "fresh" | "stale" | "unavailable";
    key_rate: null;
    inflation_yoy: null;
    updated_at: string | null;
  };
  warnings: string[];
};
