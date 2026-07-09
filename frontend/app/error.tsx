"use client";

import { DashboardError } from "@/components/dashboard-states";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <DashboardError onRetry={reset} />;
}
