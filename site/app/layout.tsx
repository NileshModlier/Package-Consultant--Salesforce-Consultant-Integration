import type { Metadata } from "next";
import { IBM_Plex_Mono, Source_Sans_3, Syne } from "next/font/google";
import "./globals.css";

const source = Source_Sans_3({
  variable: "--font-source",
  subsets: ["latin"],
});

const display = Syne({
  variable: "--font-display",
  subsets: ["latin"],
});

const plex = IBM_Plex_Mono({
  variable: "--font-plex",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Intake-to-Salesforce · Technical case study",
  description:
    "Recruiter case study of an idempotent Lead and Case integration, platform-event status sync, and a tested retry matrix. Source and local tests. Not deployed to an org.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${source.variable} ${display.variable} ${plex.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
