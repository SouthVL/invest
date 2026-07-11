import type { CurrentMacroResponse, DashboardData } from "@/lib/types";

export function applyMacroSnapshot(dashboard: DashboardData, snapshot: CurrentMacroResponse): DashboardData {
  return {
    ...dashboard,
    macro: {
      status: snapshot.status,
      key_rate: snapshot.key_rate?.value_percent ?? null,
      key_rate_period: snapshot.key_rate?.effective_date ?? null,
      key_rate_updated_at: snapshot.key_rate?.fetched_at ?? null,
      key_rate_quality: snapshot.key_rate?.quality_status ?? null,
      ruonia: snapshot.ruonia?.value_percent ?? null,
      ruonia_period: snapshot.ruonia?.rate_date ?? null,
      ruonia_publication_date: snapshot.ruonia?.publication_date ?? null,
      ruonia_updated_at: snapshot.ruonia?.fetched_at ?? null,
      ruonia_quality: snapshot.ruonia?.quality_status ?? null,
      inflation_yoy: snapshot.annual_inflation?.value_percent_yoy ?? null,
      inflation_period: snapshot.annual_inflation?.period ?? null,
      inflation_updated_at: snapshot.annual_inflation?.fetched_at ?? null,
      inflation_quality: snapshot.annual_inflation?.quality_status ?? null,
      updated_at: snapshot.generated_at
    },
    warnings: [...new Set([...dashboard.warnings, ...snapshot.warnings])]
  };
}
