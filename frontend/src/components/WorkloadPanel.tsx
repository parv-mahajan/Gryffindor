import type { WorkloadRow } from "../types";

export default function WorkloadPanel({ rows }: { rows: WorkloadRow[] }) {
  if (rows.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Department load
        </h2>
        <p className="mt-2 text-sm text-slate-400">No open work.</p>
      </section>
    );
  }

  const peak = Math.max(...rows.map((row) => row.capacity || row.open), 1);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Department load
      </h2>
      <p className="mt-0.5 text-xs text-slate-500">
        Open tickets against the capacity configured for each team.
      </p>
      <ul className="mt-4 space-y-3">
        {rows.map((row) => {
          const ratio = row.capacity ? Math.min(1, row.open / row.capacity) : 1;
          const over = row.capacity ? row.open > row.capacity : false;
          const width = `${(row.open / peak) * 100}%`;
          return (
            <li key={row.department_key}>
              <div className="flex items-baseline justify-between text-xs">
                <span className="font-medium text-slate-700">{row.name}</span>
                <span className="text-slate-500">
                  {row.open} open
                  {row.capacity ? ` / ${row.capacity}` : ""}
                  {row.overdue > 0 ? (
                    <span className="ml-2 rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-rose-600">
                      {row.overdue} overdue
                    </span>
                  ) : null}
                </span>
              </div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${over ? "bg-rose-500" : "bg-brand-500"}`}
                  style={{ width }}
                />
              </div>
              <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
                <span>
                  {Object.entries(row.by_status)
                    .map(([status, count]) => `${status} ${count}`)
                    .join(" · ")}
                </span>
                <span>avg priority {row.avg_priority}</span>
              </div>
              {row.utilisation !== null ? (
                <p className="text-[11px] text-slate-400">
                  {Math.round(ratio * 100)}% of capacity used
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
