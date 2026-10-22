export const STATUS_LABELS: Record<string, string> = {
  submitted: "Submitted",
  triaged: "Triaged",
  assigned: "Assigned",
  in_progress: "In progress",
  resolved: "Resolved",
};

export const BAND_STYLES: Record<string, string> = {
  critical: "bg-rose-100 text-rose-700 ring-rose-200",
  high: "bg-orange-100 text-orange-700 ring-orange-200",
  medium: "bg-amber-100 text-amber-700 ring-amber-200",
  low: "bg-slate-100 text-slate-600 ring-slate-200",
};

export const CATEGORY_LABELS: Record<string, string> = {
  pothole: "Pothole",
  garbage: "Garbage",
  water_leak: "Water leak",
  streetlight: "Streetlight",
  drainage: "Drainage",
  other: "Other",
};

export const CATEGORY_COLORS: Record<string, string> = {
  pothole: "#f43f5e",
  garbage: "#10b981",
  water_leak: "#3b82f6",
  streetlight: "#f59e0b",
  drainage: "#8b5cf6",
  other: "#64748b",
};

export const CATEGORY_KEYS = Object.keys(CATEGORY_LABELS);

export function categoryLabel(key: string | null | undefined): string {
  if (!key) return "Unclassified";
  return CATEGORY_LABELS[key] ?? key.replace(/_/g, " ");
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status.replace(/_/g, " ");
}

export function bandClass(band: string): string {
  return BAND_STYLES[band] ?? BAND_STYLES.low;
}

export function ageInDays(iso: string): number {
  const created = new Date(iso).getTime();
  return Math.max(0, Math.round(((Date.now() - created) / 86_400_000) * 10) / 10);
}

export function isOverdue(slaDueAt: string | null, status: string): boolean {
  if (!slaDueAt || status === "resolved") return false;
  return new Date(slaDueAt).getTime() < Date.now();
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString();
}
