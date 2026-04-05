"use client";

interface BankingConnectProps {
  authUrl: string;
}

export default function BankingConnect({ authUrl }: BankingConnectProps) {
  return (
    <div className="card border-primary-200 bg-primary-50 my-4">
      <div className="flex items-start gap-4">
        <div className="text-2xl">🏦</div>
        <div className="flex-1">
          <h4 className="font-semibold text-primary-800 mb-1">
            Connect Your Bank Account
          </h4>
          <p className="text-sm text-gray-600 mb-3">
            Securely link your bank account via Open Banking to verify your
            income and review expenses. Your data is encrypted and protected
            under PSD2 regulations.
          </p>
          <a
            href={authUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary inline-block text-sm px-5 py-2"
          >
            Connect via TrueLayer
          </a>
          <p className="text-xs text-gray-500 mt-2">
            You will be redirected to your bank to authorise access. We can only
            read your transactions - we cannot move money.
          </p>
        </div>
      </div>
    </div>
  );
}
