import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Arca - Crypto AI Market Platform",
  description:
    "Plataforma analítica financiera de alta velocidad con MinIO Lakehouse, DuckDB OLAP, verificación factual anti-alucinación y gráficos interactivos.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="dark">
      <body className="bg-[#080c14] text-slate-100 antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
