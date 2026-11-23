import type { Metadata } from "next";
import { Chakra_Petch, Inter, JetBrains_Mono } from "next/font/google";
import { cookies, headers } from "next/headers";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import { CartProvider } from "@/lib/cart-context";
import { ToastProvider } from "@/lib/toast-context";
import { CompareProvider } from "@/lib/compare-context";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import PromoStrip from "@/components/PromoStrip";
import CompareBar from "@/components/CompareBar";
import CartFlyLayer from "@/components/CartFlyLayer";
import "./globals.css";

const chakraPetch = Chakra_Petch({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-chakra-petch",
  preload: false,
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
  preload: false,
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains-mono",
  preload: false,
});

export const metadata: Metadata = {
  title: "Clickbound Commerce",
  description: "Neon-synthwave storefront.",
};

export const dynamic = "force-dynamic";

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const headerStore = await headers();
  const nonce = headerStore.get("x-nonce") ?? undefined;
  const token = cookieStore.get("token")?.value;
  const payload = token ? verifyToken(token) : null;

  const user = payload
    ? await prisma.user.findUnique({
        where: { id: payload.userId },
        select: { name: true, email: true, role: true },
      })
    : null;

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${chakraPetch.variable} ${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <head>
        <script
          nonce={nonce}
          dangerouslySetInnerHTML={{
            __html: "document.documentElement.classList.add('js')",
          }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        <div aria-hidden className="fixed inset-0 -z-10 overflow-hidden">
          <div className="ambience-blob blob-cyan" />
          <div className="ambience-blob blob-pink" />
          <div className="ambience-blob blob-purple" />
          <div className="grid-overlay" />
          <div className="vignette" />
        </div>
        <ToastProvider>
          <CartProvider>
            <CompareProvider>
              <PromoStrip />
              <Header user={user ? { name: user.name, email: user.email, role: user.role } : null} />
              <div className="flex-1">{children}</div>
              <Footer />
              <CompareBar />
              <CartFlyLayer />
            </CompareProvider>
          </CartProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
