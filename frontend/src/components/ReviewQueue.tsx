import { useState } from "react";

import { api } from "../api";
import { CATEGORY_KEYS, categoryLabel } from "../format";
import type { Complaint } from "../types";

interface Props {
  complaints: Complaint[];
  onChanged: () => void;
}

export default function ReviewQueue({ complaints, onChanged }: Props) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(
    complaint: Complaint,
    categoryKey: string,
    confirm: boolean,
  ) {
    setBusyId(complaint.id);
    setError(null);
    try {
      await api.reviewComplaint(complaint.id, categoryKey, confirm, "reviewed from queue");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setBusyId(null);
    }
  }

  if (complaints.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Human review queue
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Nothing is waiting for a human decision.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-amber-200 bg-white shadow-sm">
      <div className="border-b border-amber-100 px-5 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-amber-700">
          Human review queue
        </h2>
        <p className="mt-0.5 text-xs text-amber-700/80">
          {complaints.length} report{complaints.length === 1 ? "" : "s"} the model was not
          sure about.
        </p>
      </div>
      <ul className="divide-y divide-slate-100">
        {complaints.slice(0, 8).map((complaint) => {
          const busy = busyId === complaint.id;
          const reason = complaint.category_explanation?.review_reason;
          return (
            <li key={complaint.id} className="px-5 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-mono text-xs text-slate-500">
                    {complaint.ticket_id}
                  </p>
                  <p className="mt-0.5 text-sm text-slate-700">{complaint.description}</p>
                </div>
                <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                  {complaint.category_confidence !== null
                    ? `${Math.round(complaint.category_confidence * 100)}%`
                    : "n/a"}
                </span>
              </div>

              {reason ? (
                <p className="mt-1.5 rounded bg-amber-50 px-2 py-1 text-[11px] text-amber-800">
                  {reason}
                </p>
              ) : null}

              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={busy || !complaint.category_key}
                  onClick={() =>
                    decide(complaint, complaint.category_key as string, true)
                  }
                  className="rounded bg-brand-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
                >
                  Confirm {categoryLabel(complaint.category_key)}
                </button>
                <select
                  defaultValue=""
                  disabled={busy}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (!value) return;
                    event.target.value = "";
                    void decide(complaint, value, false);
                  }}
                  className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-[11px] text-slate-700 outline-none focus:border-brand-500"
                >
                  <option value="">Override with…</option>
                  {CATEGORY_KEYS.map((key) => (
                    <option key={key} value={key}>
                      {categoryLabel(key)}
                    </option>
                  ))}
                </select>
              </div>
            </li>
          );
        })}
      </ul>
      {error ? (
        <p className="border-t border-slate-100 px-5 py-2 text-xs text-rose-600">{error}</p>
      ) : null}
    </section>
  );
}
