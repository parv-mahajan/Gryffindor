import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

import { CATEGORY_COLORS, categoryLabel } from "../format";
import type { Hotspot } from "../types";

interface Props {
  hotspots: Hotspot[];
}

const CENTER: [number, number] = [19.076, 72.8777];

export default function HotspotPanel({ hotspots }: Props) {
  if (hotspots.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Recurring hotspots
        </h2>
        <p className="mt-2 text-sm text-slate-400">No cluster has repeated yet.</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Recurring hotspots
      </h2>
      <p className="mt-0.5 text-xs text-slate-500">
        Places where the same kind of problem keeps coming back.
      </p>

      <ul className="mt-4 space-y-2">
        {hotspots.slice(0, 5).map((spot) => (
          <li
            key={`${spot.category_key}-${spot.lat}-${spot.lng}`}
            className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2 text-xs"
          >
            <span className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: CATEGORY_COLORS[spot.category_key] ?? "#64748b" }}
              />
              <span className="font-medium text-slate-700">
                {categoryLabel(spot.category_key)}
              </span>
            </span>
            <span className="text-slate-500">
              {spot.count} reports · {spot.months_active} months
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-4">
        <MapContainer center={CENTER} zoom={15} className="h-56 w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {hotspots.map((spot) => (
            <CircleMarker
              key={`${spot.category_key}-${spot.lat}-${spot.lng}-map`}
              center={[spot.lat, spot.lng]}
              radius={Math.min(6 + spot.count * 2.5, 26)}
              pathOptions={{
                color: CATEGORY_COLORS[spot.category_key] ?? "#64748b",
                fillColor: CATEGORY_COLORS[spot.category_key] ?? "#64748b",
                fillOpacity: 0.35,
                weight: 2,
              }}
            >
              <Popup>
                <strong>{categoryLabel(spot.category_key)}</strong>
                <br />
                {spot.count} reports over {spot.months_active} months
                <br />
                oldest {spot.oldest_days} days ago
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </section>
  );
}
