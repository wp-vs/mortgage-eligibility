interface IncomeAnalysisProps {
  salaryFrequency: string | null;
  salaryRegularityScore: number | null;
  averageSalary: number | null;
  salaryVariationPct: number | null;
}

export default function IncomeAnalysis({
  salaryFrequency,
  salaryRegularityScore,
  averageSalary,
  salaryVariationPct,
}: IncomeAnalysisProps) {
  const regularityColor =
    (salaryRegularityScore || 0) >= 70
      ? "text-green-600"
      : (salaryRegularityScore || 0) >= 40
        ? "text-amber-600"
        : "text-red-600";

  return (
    <div className="card">
      <h3 className="font-semibold text-lg mb-4">Income Analysis</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-gray-500 uppercase">Frequency</div>
          <div className="font-medium capitalize">
            {salaryFrequency || "Unknown"}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">Regularity</div>
          <div className={`font-medium ${regularityColor}`}>
            {salaryRegularityScore !== null
              ? `${salaryRegularityScore}/100`
              : "N/A"}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">Avg. Salary</div>
          <div className="font-medium">
            {averageSalary
              ? `£${averageSalary.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
              : "N/A"}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">Variation</div>
          <div className="font-medium">
            {salaryVariationPct !== null ? `${salaryVariationPct}%` : "N/A"}
          </div>
        </div>
      </div>
    </div>
  );
}
