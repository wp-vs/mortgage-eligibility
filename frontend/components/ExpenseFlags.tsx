interface FlaggedExpense {
  category: string;
  description: string;
  monthly_amount: number;
  severity: "info" | "warning" | "critical";
}

interface ExpenseFlagsProps {
  flaggedExpenses: FlaggedExpense[];
  estimatedMonthlyRent: number | null;
  totalMonthlyCommitments: number | null;
}

export default function ExpenseFlags({
  flaggedExpenses,
  estimatedMonthlyRent,
  totalMonthlyCommitments,
}: ExpenseFlagsProps) {
  const severityStyles = {
    critical: "bg-red-50 border-red-200 text-red-800",
    warning: "bg-amber-50 border-amber-200 text-amber-800",
    info: "bg-blue-50 border-blue-200 text-blue-800",
  };

  const severityIcons = {
    critical: "🚨",
    warning: "⚠️",
    info: "ℹ️",
  };

  return (
    <div className="card">
      <h3 className="font-semibold text-lg mb-4">Expense Analysis</h3>

      {estimatedMonthlyRent && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <span className="text-sm text-gray-600">Estimated monthly rent:</span>
          <span className="ml-2 font-semibold">
            £{estimatedMonthlyRent.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </span>
        </div>
      )}

      {flaggedExpenses.length === 0 ? (
        <p className="text-sm text-gray-500">
          No notable expenses flagged from transaction analysis.
        </p>
      ) : (
        <div className="space-y-2">
          {flaggedExpenses.map((expense, i) => (
            <div
              key={i}
              className={`flex items-center justify-between p-3 rounded-lg border ${severityStyles[expense.severity]}`}
            >
              <div className="flex items-center gap-2">
                <span>{severityIcons[expense.severity]}</span>
                <div>
                  <div className="text-sm font-medium">
                    {expense.description}
                  </div>
                  <div className="text-xs opacity-75">{expense.category}</div>
                </div>
              </div>
              <div className="font-semibold text-sm">
                £{expense.monthly_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                <span className="text-xs font-normal">/mo</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {totalMonthlyCommitments !== null && totalMonthlyCommitments > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between items-center">
          <span className="text-sm font-medium text-gray-700">
            Total Monthly Commitments
          </span>
          <span className="text-lg font-bold text-gray-900">
            £{totalMonthlyCommitments.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </span>
        </div>
      )}
    </div>
  );
}
