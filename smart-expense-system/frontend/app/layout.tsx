import type { Metadata } from "next";
import { Bricolage_Grotesque, Azeret_Mono, DM_Sans } from "next/font/google";
import "./globals.css";

const bricolageGrotesque = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const azeretMono = Azeret_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600"],
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ExpenseIQ — Smart Expense Intelligence",
  description: "AI-powered Nigerian bank transaction classifier — BERT · Few-Shot · Graph Networks",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${bricolageGrotesque.variable} ${azeretMono.variable} ${dmSans.variable}`}>
      <body className="bg-void text-text-primary antialiased font-body">
        {children}
      </body>
    </html>
  );
}
