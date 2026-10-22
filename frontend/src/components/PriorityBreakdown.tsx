import type { PriorityExplanation } from "../types";

const FACTOR_ORDER = [
  "safety_risk",
  "severity",
  "community_impact",
  "wait_time",
  "related_reports",
];

const COLORS: Record<string, string> = {
  safety_risk: "bg-rose-500",
  severity: "bg-orange-500",
  community_impact: "bg-violet-500",
  wait_time: "bg-sky-500",
  related_reports: "bg-emerald-500",
};

interface Props {
  explanation: PriorityExplanation | null;
  score?: number;
  band?: string;
}

export default function PriorityBreakdown({ explanation, score, band }: Props) {
  if (!explanation) {
    return (
      <p className="text-sm text-slate-500">
        Priority breakdown is computed when the report is triaged.
      </p>
    );
  }

  const max = Math.max(...Object.values(explanation.contributions), 1);

  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-semibold text-slate-900">
          {score !== undefined ? score : explanation.base_score}
        </span>
        <span className="text-sm text-slate-500">/ 100</span>
        {band ? (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-slate-600">
            {band}
          </span>
        ) : null}
      </div>

      <ul className="space-y-2">
        {FACTOR_ORDER.map((key) => {
          const contribution = explanation.contributions[key] ?? 0;
          const weight = explanation.weights[key] ?? 0;
          const factor = explanation.factors[key] ?? 0;
          const width = `${(contribution / max) * 100}%`;
          return (
            <li key={key} className="text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-700">
                  {explanation.labels[key] ?? key}
                  <span className="ml-2 text-xs text-slate-400">
                    weight {weight} · factor {factor.toFixed(2)}
                  </span>
                </span>
                <span className="font-semibold text-slate-800">+{contribution}</span>
              </div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${COLORS[key] ?? "bg-slate-400"}`}
                  style={{ width }}
                />
              </div>
            </li>
          );
        })}
      </ul>

      {explanation.sla_boost > 0 ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          SLA escalation: past the {explanation.sla_hours}h target, +{explanation.sla_boost} points.
        </p>
      ) : null}

      <p className="text-xs text-slate-500">{explanation.summary}</p>
    </div>
  );
}
