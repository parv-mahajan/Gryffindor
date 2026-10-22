const TOKEN_KEY = "civicsense.token";
const SESSION_KEY = "civicsense.session";

export interface Session {
  token: string;
  username: string;
  role: string;
  display_name: string;
  expires_at: string;
}

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function saveSession(session: Session): void {
  localStorage.setItem(TOKEN_KEY, session.token);
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(SESSION_KEY);
}

export function token(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function isAdmin(session: Session | null): boolean {
  return session?.role === "admin";
}
