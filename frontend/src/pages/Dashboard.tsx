import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../api";
import AddReport from "../components/AddReport";
import ComplaintDetail from "../components/ComplaintDetail";
import DuplicateInbox from "../components/DuplicateInbox";
import HotspotPanel from "../components/HotspotPanel";
import ReviewQueue from "../components/ReviewQueue";
import WorkloadPanel from "../components/WorkloadPanel";
import {
  ageInDays,
  bandClass,
  categoryLabel,
  isOverdue,
  statusLabel,
} from "../format";
import type { Complaint, Hotspot, LinkSuggestion, Overview, WorkloadRow } from "../types";

const STATUS_OPTIONS = ["submitted", "triaged", "assigned", "in_progress", "resolved"];

const REFRESH_MS = 20_000;

interface Filters {
  status: string;
  category: string;
  department: string;
  q: string;
  needs_review: boolean;
}

const EMPTY_FILTERS: Filters = {
  status: "",
  category: "",
  department: "",
  q: "",
  needs_review: false,
};

export default function Dashboard() {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [workload, setWorkload] = useState<WorkloadRow[]>([]);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [links, setLinks] = useState<LinkSuggestion[]>([]);
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [showAddReport, setShowAddReport] = useState(false);

  const load = useCallback(
    async (options: { quiet?: boolean } = {}) => {
      if (!options.quiet) {
        setLoading(true);
      }
      try {
        const [rows, stats, load2, spots, pending] = await Promise.all([
          api.listComplaints({
            status: filters.status || undefined,
            category: filters.category || undefined,
            department: filters.department || undefined,
            q: filters.q || undefined,
            needs_review: filters.needs_review ? true : undefined,
            limit: 200,
          }),
          api.overview(),
          api.workload(),
          api.hotspots(),
          api.listLinks("pending"),
        ]);
        setComplaints(rows);
        setOverview(stats);
        setWorkload(load2);
        setHotspots(spots);
        setLinks(pending);
        setSelected((current) =>
          current ? rows.find((row) => row.id === current.id) ?? null : null,
        );
        setError(null);
        setUpdatedAt(new Date());
      } catch (err) {
        if (!options.quiet) {
          setError(err instanceof Error ? err.message : "Could not load the dashboard");
        }
      } finally {
        if (!options.quiet) {
          setLoading(false);
        }
      }
    },
    [filters],
  );

  useEffect(() => {
    void load();
  }, [load]);

  // Keep the queue in step with the database: anything added, edited or
  // removed on the server appears here without a manual reload.
  useEffect(() => {
    const timer = window.setInterval(() => {
      void load({ quiet: true });
    }, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  const reviewQueue = useMemo(
    () => complaints.filter((row) => row.needs_review),
    [complaints],
  );

  const openCount = complaints.filter((row) => row.status !== "resolved").length;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Operations dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">
            Triage queue, human review, duplicate matching and department load for the
            campus estate.
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Live from the database
            {updatedAt
              ? ` · updated ${updatedAt.toLocaleTimeString()}`
              : ""}{" "}
            · refreshes every {REFRESH_MS / 1000}s
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setShowAddReport((value) => !value)}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-500"
          >
            {showAddReport ? "Close form" : "+ Add location"}
          </button>
        </div>
      </header>

      {showAddReport ? (
        <AddReport
          onCreated={() => {
            void load();
          }}
        />
      ) : null}

      {overview ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Reports" value={overview.total} hint={`${openCount} open in view`} />
          <StatCard
            label="Needs review"
            value={overview.needs_review}
            hint="low confidence or ambiguous"
            tone={overview.needs_review > 0 ? "warn" : "calm"}
          />
          <StatCard
            label="Duplicate candidates"
            value={overview.pending_links}
            hint="waiting for a decision"
            tone={overview.pending_links > 0 ? "warn" : "calm"}
          />
          <StatCard
            label="Hotspot clusters"
            value={hotspots.length}
            hint={`${hotspots[0]?.count ?? 0} reports in the worst cluster`}
          />
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-6">
          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-5 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                  Priority queue
                </h2>
                <span className="text-xs text-slate-400">
                  {loading ? "loading…" : `${complaints.length} complaints`}
                </span>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                <input
                  value={filters.q}
                  onChange={(event) =>
                    setFilters({ ...filters, q: event.target.value })
                  }
                  placeholder="Search descriptions…"
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
                <select
                  value={filters.status}
                  onChange={(event) =>
                    setFilters({ ...filters, status: event.target.value })
                  }
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-brand-500"
                >
                  <option value="">All statuses</option>
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {statusLabel(option)}
                    </option>
                  ))}
                </select>
                <select
                  value={filters.category}
                  onChange={(event) =>
                    setFilters({ ...filters, category: event.target.value })
                  }
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-brand-500"
                >
                  <option value="">All categories</option>
                  {Object.entries({
                    pothole: "Pothole",
                    garbage: "Garbage",
                    water_leak: "Water leak",
                    streetlight: "Streetlight",
                    drainage: "Drainage",
                    other: "Other",
                  }).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
                <select
                  value={filters.department}
                  onChange={(event) =>
                    setFilters({ ...filters, department: event.target.value })
                  }
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-brand-500"
                >
                  <option value="">All departments</option>
                  {workload.map((row) => (
                    <option key={row.department_key} value={row.department_key}>
                      {row.name}
                    </option>
                  ))}
                </select>
              </div>
              <label className="mt-3 inline-flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={filters.needs_review}
                  onChange={(event) =>
                    setFilters({ ...filters, needs_review: event.target.checked })
                  }
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                Only complaints waiting for human review
              </label>
            </div>

            {error ? (
              <p className="px-5 py-4 text-sm text-rose-600">{error}</p>
            ) : null}

            <div className="max-h-[32rem] overflow-auto">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-2 font-medium">Ticket</th>
                    <th className="px-3 py-2 font-medium">Category</th>
                    <th className="px-3 py-2 font-medium">Priority</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Department</th>
                    <th className="px-5 py-2 font-medium">Age</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {complaints.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => setSelected(row)}
                      className={`cursor-pointer transition hover:bg-brand-50/60 ${
                        selected?.id === row.id ? "bg-brand-50" : ""
                      }`}
                    >
                      <td className="px-5 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-slate-700">
                            {row.ticket_id}
                          </span>
                          {row.needs_review ? (
                            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-700">
                              review
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-0.5 max-w-[18rem] truncate text-xs text-slate-500">
                          {row.description}
                        </p>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-600">
                        {categoryLabel(row.category_key)}
                        {row.category_confidence !== null ? (
                          <span className="ml-1 text-slate-400">
                            {Math.round(row.category_confidence * 100)}%
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2.5">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${bandClass(
                            row.priority_band,
                          )}`}
                        >
                          {row.priority_score.toFixed(0)}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-600">
                        {statusLabel(row.status)}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-600">
                        {row.department_key ?? "—"}
                      </td>
                      <td className="px-5 py-2.5 text-xs">
                        <span className="text-slate-600">{ageInDays(row.created_at)}d</span>
                        {isOverdue(row.sla_due_at, row.status) ? (
                          <span className="ml-2 rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-rose-600">
                            sla
                          </span>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                  {!loading && complaints.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-5 py-8 text-center text-sm text-slate-400">
                        No complaint matches these filters.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

          <DuplicateInbox links={links} onChanged={() => void load()} />
        </div>

        <div className="space-y-6">
          {selected ? (
            <ComplaintDetail
              complaint={selected}
              onChanged={() => void load()}
              onClose={() => setSelected(null)}
            />
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
              Select a complaint from the queue to see the AI reasoning, priority
              breakdown and duplicate matches.
            </div>
          )}

          <ReviewQueue complaints={reviewQueue} onChanged={() => void load()} />
          <WorkloadPanel rows={workload} />
          <HotspotPanel hotspots={hotspots} />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  hint,
  tone = "calm",
}: {
  label: string;
  value: number;
  hint: string;
  tone?: "calm" | "warn";
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p
        className={`mt-1 text-2xl font-semibold ${
          tone === "warn" && value > 0 ? "text-amber-600" : "text-slate-900"
        }`}
      >
        {value}
      </p>
      <p className="mt-0.5 text-xs text-slate-400">{hint}</p>
    </div>
  );
}
