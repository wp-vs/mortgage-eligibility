"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createCustomer } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleStart() {
    setLoading(true);
    try {
      const customer = await createCustomer();
      localStorage.setItem("customerId", String(customer.id));
      router.push("/chat");
    } catch {
      alert("Failed to start session. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-20">
      <div className="text-center space-y-8">
        <h1 className="text-5xl font-bold text-gray-900 leading-tight">
          Find the right mortgage,
          <br />
          <span className="text-primary-600">without the hassle</span>
        </h1>

        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Chat with our AI assistant to explore your borrowing options. Connect
          your bank account for instant income verification, and get matched
          with the best mortgage products for your situation.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <button
            onClick={handleStart}
            disabled={loading}
            className="btn-primary text-lg px-10 py-4"
          >
            {loading ? "Setting up..." : "Get Started"}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-12">
          <div className="card text-center">
            <div className="text-3xl mb-3">💬</div>
            <h3 className="font-semibold text-lg mb-2">Chat with AI</h3>
            <p className="text-gray-500 text-sm">
              Our assistant walks you through your needs conversationally - no
              long forms to fill out.
            </p>
          </div>

          <div className="card text-center">
            <div className="text-3xl mb-3">🏦</div>
            <h3 className="font-semibold text-lg mb-2">Open Banking</h3>
            <p className="text-gray-500 text-sm">
              Securely connect your bank to verify income and understand your
              financial position.
            </p>
          </div>

          <div className="card text-center">
            <div className="text-3xl mb-3">✅</div>
            <h3 className="font-semibold text-lg mb-2">Broker Review</h3>
            <p className="text-gray-500 text-sm">
              A qualified broker reviews your matched products before any
              recommendation is finalised.
            </p>
          </div>
        </div>

        <p className="text-xs text-gray-400 pt-8">
          MortgageMatch is an execution-only service. We do not provide
          financial advice. All product information is presented for your
          consideration and will be reviewed by a qualified mortgage broker.
        </p>
      </div>
    </div>
  );
}
