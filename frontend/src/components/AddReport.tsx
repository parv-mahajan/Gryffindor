import { useState } from "react";

import { api } from "../api";
import MapPicker, { type LatLng } from "./MapPicker";

const DEFAULT_POINT: LatLng = { lat: 19.076, lng: 72.8777 };

interface Props {
  onCreated: () => void;
}

export default function AddReport({ onCreated }: Props) {
  const [description, setDescription] = useState("");
  const [point, setPoint] = useState<LatLng>(DEFAULT_POINT);
  const [reporterName, setReporterName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const form = new FormData();
      form.append("description", description.trim());
      form.append("lat", String(point.lat));
      form.append("lng", String(point.lng));
      if (reporterName.trim()) form.append("reporter_name", reporterName.trim());

      const created = await api.createComplaint(form);
      const duplicates = created.duplicates?.length ?? 0;
      setDone(
        `Created ${created.ticket_id} in ${created.complaint.department_key ?? "no department"}` +
          (duplicates
            ? ` · matched ${duplicates} existing report${duplicates === 1 ? "" : "s"}`
            : ""),
      );
      setDescription("");
      setReporterName("");
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the report");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-brand-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-brand-700">
          Add a location
        </h2>
        <p className="text-xs text-slate-500">
          Click the map to drop the pin, or type the coordinates below.
        </p>
      </div>

      <form className="mt-4 grid gap-5 lg:grid-cols-[1.1fr_1fr]" onSubmit={handleSubmit}>
        <div>
          <MapPicker value={point} onChange={setPoint} />

          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className="block">
              <span className="mb-1 block text-xs text-slate-500">Latitude</span>
              <input
                type="number"
                step="0.000001"
                value={point.lat}
                onChange={(event) =>
                  setPoint({ ...point, lat: Number(event.target.value) })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs text-slate-500">Longitude</span>
              <input
                type="number"
                step="0.000001"
                value={point.lng}
                onChange={(event) =>
                  setPoint({ ...point, lng: Number(event.target.value) })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>

          <p className="mt-2 text-xs text-slate-500">
            Coordinates:{" "}
            <span className="font-mono text-slate-700">
              {point.lat.toFixed(6)}, {point.lng.toFixed(6)}
            </span>
          </p>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              What is happening there?
            </span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              required
              minLength={5}
              placeholder="e.g. water pipeline burst near the sports complex"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              Reported by (optional)
            </span>
            <input
              value={reporterName}
              onChange={(event) => setReporterName(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>

          {error ? (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
          ) : null}
          {done ? (
            <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {done}
            </p>
          ) : null}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy || description.trim().length < 5}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {busy ? "Saving…" : "Save location"}
            </button>
            <button
              type="button"
              onClick={() => setPoint(DEFAULT_POINT)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
            >
              Reset pin
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
