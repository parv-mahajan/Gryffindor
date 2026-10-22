export type PriorityBand = "critical" | "high" | "medium" | "low";

export interface CategoryAlternative {
  key: string;
  name?: string;
  confidence: number;
  explanation?: string;
}

export interface CategoryExplanation {
  method?: string;
  summary?: string;
  matched_keywords?: string[];
  nearest_prototype?: string;
  prototype_similarity?: number;
  keyword_confidence?: number;
  embedding_confidence?: number;
  image_confidence?: number | null;
  image_category?: string | null;
  review_reason?: string | null;
}

export interface Complaint {
  id: number;
  ticket_id: string;
  description: string;
  status: string;
  lat: number;
  lng: number;
  incident_id: number | null;
  category_key: string | null;
  category_confidence: number | null;
  category_explanation: CategoryExplanation | null;
  category_alternatives: CategoryAlternative[] | null;
  needs_review: boolean;
  image_scores: Record<string, unknown> | null;
  model_version: string | null;
  priority_score: number;
  priority_band: PriorityBand;
  priority_factors: Record<string, number> | null;
  priority_contributions: Record<string, number> | null;
  priority_overridden: boolean;
  department_key: string | null;
  sla_due_at: string | null;
  reporter_name: string | null;
  reporter_contact: string | null;
  photos: string[] | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface PriorityExplanation {
  factors: Record<string, number>;
  contributions: Record<string, number>;
  labels: Record<string, string>;
  weights: Record<string, number>;
  base_score: number;
  sla_boost: number;
  sla_hours: number;
  sla_due_at: string;
  sla_breached: boolean;
  age_hours: number;
  evidence: Record<string, unknown>;
  summary: string;
}

export interface CreateComplaintResponse {
  ticket_id: string;
  complaint: Complaint;
  classification: {
    category: string;
    category_name: string;
    confidence: number;
    explanation: CategoryExplanation;
    alternatives: CategoryAlternative[];
    needs_review: boolean;
  } | null;
  priority: PriorityExplanation | null;
  duplicates: DuplicateMatch[];
}

export interface TicketStatus {
  ticket_id: string;
  status: string;
  category: string | null;
  category_confidence: number | null;
  priority_band: PriorityBand | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  last_update: string | null;
  department: string | null;
  incident_ticket_id: string | null;
  grouped_reports: number;
}

export interface ComplaintLink {
  id: number;
  complaint_id: number;
  linked_complaint_id: number;
  relation: "duplicate" | "related";
  score: number;
  text_similarity: number;
  geo_proximity: number;
  time_decay: number;
  distance_m: number;
  status: string;
}

export interface LinkSuggestion extends ComplaintLink {
  first: LinkSide;
  second: LinkSide;
}

export interface LinkSide {
  ticket_id: string | null;
  description: string | null;
  category_key: string | null;
  status: string | null;
  created_at: string | null;
}

export interface WorkloadRow {
  department_key: string;
  name: string;
  capacity: number;
  open: number;
  by_status: Record<string, number>;
  avg_priority: number;
  overdue: number;
  utilisation: number | null;
}

export interface Hotspot {
  category_key: string;
  lat: number;
  lng: number;
  count: number;
  months_active: number;
  oldest_days: number;
  ticket_ids: string[];
}

export interface Overview {
  total: number;
  open: number;
  needs_review: number;
  pending_links: number;
}

export interface ReviewResult {
  ticket_id: string;
  category_key: string;
  needs_review: boolean;
  decision: "confirmed" | "overridden";
  complaint: Complaint;
}

export interface LinkDecisionResult {
  link_id: number;
  status: string;
  merged: boolean;
  primary_ticket: string;
  secondary_ticket: string;
}

export interface DuplicateMatch {
  ticket_id: string;
  relation: "duplicate" | "related";
  score: number;
  text_similarity: number;
  geo_proximity: number;
  time_decay: number;
  distance_m: number;
}

export interface Session {
  token: string;
  username: string;
  role: string;
  display_name: string;
  expires_at: string;
}
