import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";
import { BankProvider } from "@/context/BankContext";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Sovereign — Banking Intelligence",
  description:
    "Annual report intelligence platform for banking executives: KPIs, lineage, validation, benchmarking and executive deliverables.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${playfair.variable} ${inter.variable}`}>
      <body className="min-h-full bg-ink text-text-primary antialiased">
        <BankProvider>
          <Sidebar />
          <div className="ml-64 flex min-h-screen flex-col">
            <TopBar />
            <main className="flex-1 px-10 py-10">{children}</main>
            <footer className="border-t border-border px-10 py-5 text-[10px] uppercase tracking-[0.25em] text-text-secondary/60">
              Sovereign · Banking Annual Report Intelligence · Figures in ₹
              crore unless stated
            </footer>
          </div>
        </BankProvider>
      </body>
    </html>
  );
}
