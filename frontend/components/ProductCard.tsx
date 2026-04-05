interface ProductCardProps {
  rank: number;
  lenderName: string;
  productName: string;
  rate: number;
  productType: string;
  initialPeriodMonths: number;
  maxLtv: number;
  arrangementFee: number;
  estimatedMonthlyPayment?: number;
  matchScore: number;
  matchReasons?: string[];
  unmetCriteria?: string[];
  brokerApproved?: boolean | null;
  brokerNotes?: string | null;
}

export default function ProductCard({
  rank,
  lenderName,
  productName,
  rate,
  productType,
  initialPeriodMonths,
  maxLtv,
  arrangementFee,
  estimatedMonthlyPayment,
  matchScore,
  matchReasons,
  unmetCriteria,
  brokerApproved,
  brokerNotes,
}: ProductCardProps) {
  const rankColors: Record<number, string> = {
    1: "border-yellow-400 bg-yellow-50",
    2: "border-gray-300 bg-gray-50",
    3: "border-orange-300 bg-orange-50",
  };

  return (
    <div
      className={`card border-2 ${rankColors[rank] || "border-gray-200"} relative`}
    >
      <div className="absolute -top-3 left-4 bg-white px-3 py-1 rounded-full text-xs font-bold border border-gray-200">
        #{rank} Match
      </div>

      <div className="pt-2">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="font-bold text-lg text-gray-900">{lenderName}</h3>
            <p className="text-sm text-gray-500">{productName}</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-primary-600">{rate}%</div>
            <div className="text-xs text-gray-500">
              {productType} for {initialPeriodMonths}m
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4 text-center">
          <div className="bg-gray-50 rounded-lg p-2">
            <div className="text-xs text-gray-500">Max LTV</div>
            <div className="font-semibold">{maxLtv}%</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <div className="text-xs text-gray-500">Fee</div>
            <div className="font-semibold">
              {arrangementFee > 0 ? `£${arrangementFee.toLocaleString()}` : "None"}
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <div className="text-xs text-gray-500">Est. Monthly</div>
            <div className="font-semibold">
              {estimatedMonthlyPayment
                ? `£${estimatedMonthlyPayment.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                : "N/A"}
            </div>
          </div>
        </div>

        {matchReasons && matchReasons.length > 0 && (
          <div className="mb-3">
            <div className="text-xs font-medium text-green-700 mb-1">
              Why this works:
            </div>
            <ul className="text-xs text-gray-600 space-y-0.5">
              {matchReasons.slice(0, 3).map((reason, i) => (
                <li key={i} className="flex items-start gap-1">
                  <span className="text-green-500 mt-0.5">✓</span> {reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {unmetCriteria && unmetCriteria.length > 0 && (
          <div className="mb-3">
            <div className="text-xs font-medium text-amber-700 mb-1">
              Points to note:
            </div>
            <ul className="text-xs text-gray-600 space-y-0.5">
              {unmetCriteria.slice(0, 2).map((issue, i) => (
                <li key={i} className="flex items-start gap-1">
                  <span className="text-amber-500 mt-0.5">!</span> {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        {brokerApproved !== null && brokerApproved !== undefined && (
          <div
            className={`mt-3 p-3 rounded-lg text-sm ${brokerApproved ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}
          >
            <span className="font-medium">
              Broker: {brokerApproved ? "Approved" : "Not Approved"}
            </span>
            {brokerNotes && <p className="mt-1 text-xs">{brokerNotes}</p>}
          </div>
        )}

        <div className="mt-3 flex items-center gap-2">
          <div className="flex-1 bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-primary-500 h-1.5 rounded-full"
              style={{ width: `${Math.min(matchScore, 100)}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">
            {matchScore.toFixed(0)}% match
          </span>
        </div>
      </div>
    </div>
  );
}
