import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Кооператив Юг — Портфель инвестора",
  description: "Read-only dashboard for investment portfolio analytics"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
