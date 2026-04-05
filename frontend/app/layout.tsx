import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MortgageMatch - Find Your Perfect Mortgage",
  description:
    "AI-powered mortgage brokerage. Chat with our assistant to find the best mortgage products for your needs.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <nav className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <a href="/" className="text-2xl font-bold text-primary-800">
              MortgageMatch
            </a>
            <div className="flex gap-4 text-sm">
              <a href="/chat" className="text-gray-600 hover:text-primary-600">
                Start Chat
              </a>
              <a
                href="/broker"
                className="text-gray-600 hover:text-primary-600"
              >
                Broker Login
              </a>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
