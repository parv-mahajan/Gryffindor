import { clearSession, token } from "./auth";
import type {
  Complaint,
  ComplaintLink,
  CreateComplaintResponse,
  Hotspot,
  LinkDecisionResult,
  LinkSuggestion,
  Overview,
  ReviewResult,
  Session,
  TicketStatus,
  WorkloadRow,
} from "./types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const bearer = token();
  if (bearer) {
    headers.set("Authorization", `Bearer ${bearer}`);
  } else {
    // Public endpoints still work without a session.
    headers.set("X-Actor-Id", "reporter");
  }

  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
    // Always read the current state of the database: a report added or
    // removed on the server has to show up on the next refresh.
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        detail =
          typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* keep default detail */
    }
    if (response.status === 401) {
      // The session expired: drop it so the app can send the user to the login
      // screen instead of failing every request.
      clearSession();
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export interface ComplaintFilters {
  status?: string;
  category?: string;
  department?: string;
  q?: string;
  needs_review?: boolean;
  limit?: number;
  offset?: number;
}

export const api = {
  login: (username: string, password: string) =>
    request<Session>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),

  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),

  me: () => request<Session>("/auth/me"),

  listComplaints: (filters: ComplaintFilters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        params.set(key, String(value));
      }
    });
    const query = params.toString();
    return request<Complaint[]>(`/complaints${query ? `?${query}` : ""}`);
  },

  getComplaint: (id: number) => request<Complaint>(`/complaints/${id}`),

  getComplaintLinks: (id: number) => request<ComplaintLink[]>(`/complaints/${id}/links`),

  createComplaint: (form: FormData) =>
    request<CreateComplaintResponse>("/complaints", { method: "POST", body: form }),

  getTicket: (ticketId: string) =>
    request<TicketStatus>(`/tickets/${encodeURIComponent(ticketId)}`),

  overview: () => request<Overview>("/complaints/stats/overview"),

  workload: () => request<WorkloadRow[]>("/complaints/stats/workload"),

  hotspots: () => request<Hotspot[]>("/complaints/stats/hotspots"),

  listLinks: (status = "pending") =>
    request<LinkSuggestion[]>(`/complaints/links?status=${status}`),

  changeStatus: (id: number, status: string, reason?: string) =>
    request<Complaint>(`/complaints/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, reason }),
    }),

  reviewComplaint: (
    id: number,
    categoryKey: string,
    confirm: boolean,
    reason?: string,
  ) =>
    request<ReviewResult>(`/complaints/${id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category_key: categoryKey, confirm, reason }),
    }),

  decideLink: (
    linkId: number,
    decision: "accepted" | "rejected",
    reason?: string,
  ) =>
    request<LinkDecisionResult>(`/complaints/links/${linkId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reason }),
    }),
};
