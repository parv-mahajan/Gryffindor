import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import MapPicker, { type LatLng } from "../components/MapPicker";
import PriorityBreakdown from "../components/PriorityBreakdown";
import type { CreateComplaintResponse } from "../types";

const DEFAULT_POINT: LatLng = { lat: 19.076, lng: 72.8777 };

export default function Submit() {
  const [description, setDescription] = useState("");
  const [point, setPoint] = useState<LatLng>(DEFAULT_POINT);
  const [reporterName, setReporterName] = useState("");
  const [reporterContact, setReporterContact] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CreateComplaintResponse | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("description", description.trim());
      form.append("lat", String(point.lat));
      form.append("lng", String(point.lng));
      if (reporterName) form.append("reporter_name", reporterName);
      if (reporterContact) form.append("reporter_contact", reporterContact);
      files.forEach((file) => form.append("photos", file));
      const response = await api.createComplaint(form);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <div className="mx-auto max-w-2xl space-y-5">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
          <h1 className="text-xl font-semibold text-emerald-900">Report submitted</h1>
          <p className="mt-1 text-sm text-emerald-800">
            Your ticket id is{" "}
            <span className="font-mono font-semibold">{result.ticket_id}</span>. Keep it to track
            progress.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Classification
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
              {result.classification?.category_name ?? result.complaint.category_key}
            </span>
            {result.classification ? (
              <span className="text-xs text-slate-500">
                {Math.round(result.classification.confidence * 100)}% confidence
              </span>
            ) : null}
            {result.classification?.needs_review ? (
              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                a human will check this
              </span>
            ) : null}
          </div>
          {result.classification?.explanation.summary ? (
            <p className="mt-2 text-sm text-slate-600">
              {result.classification.explanation.summary}
            </p>
          ) : null}
        </div>

        {result.duplicates.length > 0 ? (
          <div className="rounded-2xl border border-sky-200 bg-sky-50 p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-sky-800">
              We may already know about this
            </h2>
            <p className="mt-1 text-sm text-sky-700">
              {result.duplicates.length} similar report
              {result.duplicates.length === 1 ? "" : "s"} were filed nearby recently. The
              team will treat them as one issue, so nothing gets lost.
            </p>
            <ul className="mt-3 space-y-1.5">
              {result.duplicates.slice(0, 3).map((match) => (
                <li key={match.ticket_id} className="text-xs text-sky-900">
                  <span className="font-mono">{match.ticket_id}</span> · {match.relation} ·
                  match {Math.round(match.score * 100)}% · {Math.round(match.distance_m)} m
                  away
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Priority breakdown
          </h2>
          <PriorityBreakdown
            explanation={result.priority}
            score={result.complaint.priority_score}
            band={result.complaint.priority_band}
          />
        </div>

        <div className="flex gap-3">
          <Link
            to={`/ticket?id=${result.ticket_id}`}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500"
          >
            Track this ticket
          </Link>
          <button
            type="button"
            onClick={() => {
              setResult(null);
              setDescription("");
              setFiles([]);
            }}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Report another issue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1.05fr_1fr]">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">Report a civic issue</h1>
        <p className="mt-1 text-sm text-slate-500">
          Describe the problem, drop the pin on the map and we will classify it, score its
          priority and route it to the right department.
        </p>

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              What is the problem?
            </span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={5}
              required
              minLength={5}
              placeholder="e.g. big pit on main road near gate 2, bikes skidding"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>

          <div>
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              Where is it? (click the map or type coordinates)
            </span>
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
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
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
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </label>
            </div>
          </div>

          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              Photos (optional)
            </span>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(event) =>
                setFiles(Array.from(event.target.files ?? []).slice(0, 4))
              }
              className="w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">
                Your name (optional)
              </span>
              <input
                value={reporterName}
                onChange={(event) => setReporterName(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">
                Contact (optional)
              </span>
              <input
                value={reporterContact}
                onChange={(event) => setReporterContact(event.target.value)}
                placeholder="email or phone"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </label>
          </div>

          {error ? (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
          ) : null}

          <button
            type="submit"
            disabled={submitting || description.trim().length < 5}
            className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {submitting ? "Submitting…" : "Submit report"}
          </button>
        </form>
      </section>

      <aside className="space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            What happens next
          </h2>
          <ol className="mt-3 space-y-3 text-sm text-slate-600">
            <li>
              <span className="font-medium text-slate-800">1. Automatic classification</span>
              <p className="text-slate-500">
                The report is matched against past issues to pick a category and confidence.
              </p>
            </li>
            <li>
              <span className="font-medium text-slate-800">2. Duplicate check</span>
              <p className="text-slate-500">
                Nearby recent reports are compared; you may be asked to confirm a duplicate.
              </p>
            </li>
            <li>
              <span className="font-medium text-slate-800">3. Priority scoring</span>
              <p className="text-slate-500">
                Safety, severity, impact, waiting time and repeat reports set the priority.
              </p>
            </li>
            <li>
              <span className="font-medium text-slate-800">4. Routing</span>
              <p className="text-slate-500">
                The report is assigned to the right department with a response target.
              </p>
            </li>
          </ol>
        </div>
      </aside>
    </div>
  );
}
