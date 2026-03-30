"use client";

import { useEffect, useState } from "react";
import { brokerLogin, getBrokerCases } from "@/lib/api";

interface Case {
  customer_id: number;
  customer_name: string | null;
  status: string;
  has_banking_analysis: boolean;
  recommendation_count: number;
  created_at: string;
}

export default function BrokerDashboard() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginError(null);
    setLoading(true);
    try {
      const data = await brokerLogin(email, password);
      localStorage.setItem("brokerToken", data.access_token);
      setLoggedIn(true);
      loadCases();
    } catch {
      setLoginError("Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  async function loadCases() {
    try {
      const data = await getBrokerCases();
      setCases(data.cases || []);
    } catch {
      // Handle error
    }
  }

  useEffect(() => {
    const token = localStorage.getItem("brokerToken");
    if (token) {
      setLoggedIn(true);
      loadCases();
    }
  }, []);

  if (!loggedIn) {
    return (
      <div className="max-w-md mx-auto px-6 py-20">
        <div className="card">
          <h2 className="text-2xl font-bold text-center mb-6">Broker Login</h2>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                required
              />
            </div>
            {loginError && (
              <p className="text-red-600 text-sm">{loginError}</p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? "Logging in..." : "Log In"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Broker Dashboard</h1>
        <button
          onClick={() => {
            localStorage.removeItem("brokerToken");
            setLoggedIn(false);
          }}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Log Out
        </button>
      </div>

      {cases.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">No cases pending review.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {cases.map((c) => (
            <a
              key={c.customer_id}
              href={`/broker/case/${c.customer_id}`}
              className="card block hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">
                    {c.customer_name || `Customer #${c.customer_id}`}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {c.recommendation_count} product
                    {c.recommendation_count !== 1 ? "s" : ""} matched
                    {c.has_banking_analysis && " | Banking analysis available"}
                  </p>
                </div>
                <div className="text-right">
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                      c.status === "submitted"
                        ? "bg-amber-100 text-amber-800"
                        : c.status === "reviewed"
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {c.status}
                  </span>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(c.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
