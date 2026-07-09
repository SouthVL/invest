import { describe, expect, it } from "vitest";

import { formatMoney, formatPercent, formatReadableDate } from "./format";

describe("format helpers", () => {
  it("formats money without changing missing data semantics", () => {
    expect(formatMoney({ amount: "17615.00", currency: "RUB" })).toContain("17");
    expect(formatMoney({ amount: "unknown", currency: "RUB" })).toBe("unknown RUB");
  });

  it("formats nullable percent explicitly", () => {
    expect(formatPercent("82.74")).toBe("82.74%");
    expect(formatPercent(null)).toBe("нет данных");
  });

  it("formats iso dates for display", () => {
    expect(formatReadableDate("2026-07-01")).toBe("01.07.2026");
  });
});
