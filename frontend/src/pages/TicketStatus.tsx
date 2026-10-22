import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api";
import type { TicketStatus } from "../types";

const STEPS = ["submitted", "triaged", "assigned", "in_progress", "resolved"];

export default function TicketStatus() {
  const [params, setParams] = useSearchParams();
  const [ticketId, setTicketId] = useState(params.get("id") ?? "");
  const [ticket, setTicket] = useState<TicketStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const id = params.get("id");
    if (id) setTicketId(id);
  }, [params]);

  async function lookup(event: React.FormEvent) {
    event.preventDefault();
    if (!ticketId.trim()) return;
    setLoading(true);
    setError(null);
    setTicket(null);
    try {
      const result = await api.getTicket(ticketId.trim());
      setTicket(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lookup failed");
    } finally {
      setLoading(false);
    }
  }

  const currentIndex = ticket ? STEPS.indexOf(ticket.status) : -1;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Track a ticket</h1>
        <p className="mt-1 text-sm text-slate-500">
          Enter the ticket id you received when you reported the issue.
        </p>
      </div>

      <form onSubmit={lookup} className="flex gap-3">
        <input
          value={ticketId}
          onChange={(event) => setTicketId(event.target.value)}
          placeholder="CS-XXXXXXXX"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        <button
          type="submit"
          disabled={loading || !ticketId.trim()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:bg-slate-300"
        >
          {loading ? "Checking…" : "Track"}
        </button>
      </form>

      {error ? (
        <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
      ) : null}

      {ticket ? (
        <div className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Ticket</p>
              <p className="font-mono text-lg font-semibold text-slate-900">{ticket.ticket_id}</p>
            </div>
            <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-700">
              {ticket.status.replace("_", " ")}
            </span>
          </div>

          <ol className="flex items-center gap-1">
            {STEPS.map((step, index) => {
              const done = currentIndex >= index && currentIndex !== -1;
              const active = currentIndex === index;
              return (
                <li key={step} className="flex flex-1 flex-col gap-1">
                  <span
                    className={`h-1.5 w-full rounded-full ${
                      done ? "bg-brand-500" : "bg-slate-200"
                    } ${active ? "ring-2 ring-brand-200" : ""}`}
                  />
                  <span
                    className={`text-[11px] capitalize ${
                      done ? "font-medium text-slate-700" : "text-slate-400"
                    }`}
                  >
                    {step.replace("_", " ")}
                  </span>
                </li>
              );
            })}
          </ol>

          <dl className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-3">
              <dt className="text-xs text-slate-500">Category</dt>
              <dd className="mt-0.5 text-sm font-medium text-slate-800">
                {ticket.category ?? "pending triage"}
              </dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <dt className="text-xs text-slate-500">Priority band</dt>
              <dd className="mt-0.5 text-sm font-medium text-slate-800">
                {ticket.priority_band ?? "-"}
              </dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <dt className="text-xs text-slate-500">Reported</dt>
              <dd className="mt-0.5 text-sm font-medium text-slate-800">
                {new Date(ticket.created_at).toLocaleString()}
              </dd>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <dt className="text-xs text-slate-500">Last update</dt>
              <dd className="mt-0.5 text-sm font-medium text-slate-800">
                {new Date(ticket.updated_at).toLocaleString()}
              </dd>
            </div>
            {ticket.department ? (
              <div className="rounded-lg bg-slate-50 p-3">
                <dt className="text-xs text-slate-500">Handled by</dt>
                <dd className="mt-0.5 text-sm font-medium text-slate-800">
                  {ticket.department}
                </dd>
              </div>
            ) : null}
            {ticket.grouped_reports > 1 ? (
              <div className="rounded-lg bg-slate-50 p-3">
                <dt className="text-xs text-slate-500">Grouped reports</dt>
                <dd className="mt-0.5 text-sm font-medium text-slate-800">
                  {ticket.grouped_reports} people reported this issue
                </dd>
              </div>
            ) : null}
          </dl>

          {ticket.last_update ? (
            <p className="text-sm text-slate-600">{ticket.last_update}</p>
          ) : null}
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => {
          setTicketId("");
          setTicket(null);
          setParams({});
        }}
        className="text-sm text-slate-500 underline-offset-2 hover:underline"
      >
        Clear
      </button>
    </div>
  );
}
