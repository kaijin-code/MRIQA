import type { Metadata } from "next";
import { Noto_Sans_SC, ZCOOL_XiaoWei } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const bodyFont = Noto_Sans_SC({
  variable: "--font-body",
  subsets: ["chinese-simplified"],
  weight: ["400", "500", "700"],
});

const displayFont = ZCOOL_XiaoWei({
  variable: "--font-display",
  subsets: ["chinese-simplified"],
  weight: "400",
});

export const metadata: Metadata = {
  title: "多角色智能助手",
  description: "多角色协作的中文对话与检索界面",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${bodyFont.variable} ${displayFont.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[var(--background)] text-[var(--foreground)]">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
