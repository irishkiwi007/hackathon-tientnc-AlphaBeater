import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AlphaBeater | Risk-gated AI options agent",
  description:
    "Inspect how AlphaBeater researches factors, plans options trades, and enforces paper-trading risk controls.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
