import { useState } from "react";

import { api } from "../api";
import { categoryLabel } from "../format";
import type { LinkSuggestion } from "../types";

interface Props {
  links: LinkSuggestion[];
  onChanged: () => void;
}

export default function DuplicateInbox({ links, onChanged }: Props) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(link: LinkSuggestion, decision: "accepted" | "rejected") {
    setBusyId(link.id);
    setError(null);
    try {
      await api.decideLink(link.id, decision, "reviewed in the duplicate inbox");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Duplicate inbox
        </h2>
        <p className="mt-0.5 text-xs text-slate-500">
          Reports the matcher thinks repeat an earlier one. Merging them puts both under
          the same incident.
        </p>
      </div>

      {links.length === 0 ? (
        <p className="px-5 py-6 text-sm text-slate-400">
          No duplicate suggestions are waiting.
        </p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {links.slice(0, 6).map((link) => {
            const busy = busyId === link.id;
            const newer =
              link.second.created_at && link.first.created_at
                ? new Date(link.second.created_at) > new Date(link.first.created_at)
                : false;
            const original = newer ? link.first : link.second;
            const repeat = newer ? link.second : link.first;
            return (
              <li key={link.id} className="px-5 py-3">
                <div className="flex flex-wrap items-center gap-2 text-[11px]">
                  <span
                    className={`rounded px-1.5 py-0.5 font-semibold uppercase ${
                      link.relation === "duplicate"
                        ? "bg-rose-100 text-rose-700"
                        : "bg-sky-100 text-sky-700"
                    }`}
                  >
                    {link.relation}
                  </span>
                  <span className="text-slate-500">
                    score {link.score.toFixed(2)} · text {link.text_similarity.toFixed(2)}
                    · {link.distance_m.toFixed(0)} m
                  </span>
                </div>

                <p className="mt-1.5 text-sm text-slate-700">{original.description}</p>
                <p className="mt-0.5 font-mono text-[11px] text-slate-400">
                  {original.ticket_id} ({categoryLabel(original.category_key)}) → repeats{" "}
                  {repeat.ticket_id}
                </p>

                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void decide(link, "accepted")}
                    className="rounded bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                  >
                    Merge into one incident
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void decide(link, "rejected")}
                    className="rounded border border-slate-300 px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                  >
                    Different issues
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {error ? (
        <p className="border-t border-slate-100 px-5 py-2 text-xs text-rose-600">{error}</p>
      ) : null}
    </section>
  );
}
