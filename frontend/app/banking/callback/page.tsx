"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { bankingCallback } from "@/lib/api";

function CallbackHandler() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"processing" | "success" | "error">(
    "processing"
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state"); // connection_id

    if (!code || !state) {
      setStatus("error");
      setError("Missing authorisation code or connection reference.");
      return;
    }

    async function handleCallback() {
      try {
        await bankingCallback(code!, Number(state));
        setStatus("success");
      } catch (err) {
        setStatus("error");
        setError(
          err instanceof Error ? err.message : "Failed to connect bank account"
        );
      }
    }

    handleCallback();
  }, [searchParams]);

  return (
    <div className="max-w-lg mx-auto px-6 py-20 text-center">
      {status === "processing" && (
        <div>
          <div className="text-4xl mb-4 animate-spin">⏳</div>
          <h2 className="text-2xl font-bold mb-2">Connecting Your Bank</h2>
          <p className="text-gray-500">
            Please wait while we securely connect to your bank account and
            analyse your transactions...
          </p>
        </div>
      )}

      {status === "success" && (
        <div>
          <div className="text-4xl mb-4">✅</div>
          <h2 className="text-2xl font-bold mb-2">Bank Connected!</h2>
          <p className="text-gray-500 mb-6">
            Your bank account has been connected and your income and expenses
            have been analysed. You can now return to the chat to continue.
          </p>
          <a href="/chat" className="btn-primary inline-block">
            Return to Chat
          </a>
        </div>
      )}

      {status === "error" && (
        <div>
          <div className="text-4xl mb-4">❌</div>
          <h2 className="text-2xl font-bold mb-2">Connection Failed</h2>
          <p className="text-gray-500 mb-2">
            We were unable to connect to your bank account.
          </p>
          {error && <p className="text-red-600 text-sm mb-6">{error}</p>}
          <a href="/chat" className="btn-primary inline-block">
            Return to Chat
          </a>
        </div>
      )}
    </div>
  );
}

export default function BankingCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-lg mx-auto px-6 py-20 text-center">
          <div className="text-4xl mb-4 animate-spin">⏳</div>
          <p className="text-gray-500">Loading...</p>
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
