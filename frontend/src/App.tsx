import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { api } from "./api";
import { clearSession, loadSession, saveSession, token, type Session } from "./auth";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Submit from "./pages/Submit";
import TicketStatus from "./pages/TicketStatus";

const navLink = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
    isActive
      ? "bg-brand-600 text-white shadow-sm"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
  }`;

function AdminOnly({ children }: { children: React.ReactElement }) {
  const location = useLocation();
  const [session, setSession] = useState<Session | null>(loadSession);
  const [checking, setChecking] = useState(Boolean(token()));

  useEffect(() => {
    // Without a stored token there is nothing to check - go straight to login.
    if (!token()) {
      setChecking(false);
      return;
    }
    let active = true;
    api
      .me()
      .then((current) => {
        if (!active) return;
        saveSession(current);
        setSession(current);
      })
      .catch(() => {
        if (!active) return;
        clearSession();
        setSession(null);
      })
      .finally(() => {
        if (active) setChecking(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (checking) {
    return (
      <p className="py-16 text-center text-sm text-slate-400">Checking your session…</p>
    );
  }
  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (session.role !== "admin") {
    return (
      <div className="mx-auto max-w-md rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center">
        <h1 className="text-lg font-semibold text-amber-900">Admins only</h1>
        <p className="mt-1 text-sm text-amber-800">
          You are signed in as <span className="font-mono">{session.username}</span>. The
          operations dashboard needs an admin account.
        </p>
      </div>
    );
  }
  return children;
}

export default function App() {
  const [session, setSession] = useState<Session | null>(loadSession);

  async function signOut() {
    try {
      await api.logout();
    } catch {
      /* the token is gone either way */
    }
    clearSession();
    setSession(null);
  }

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-lg font-bold text-white">
              C
            </div>
            <div>
              <p className="text-base font-semibold leading-tight text-slate-900">
                CivicSense
              </p>
              <p className="text-xs text-slate-500">Civic intelligence &amp; issue resolution</p>
            </div>
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navLink}>
              Report an issue
            </NavLink>
            <NavLink to="/ticket" className={navLink}>
              Track a ticket
            </NavLink>
            <NavLink to="/dashboard" className={navLink}>
              Operations
            </NavLink>
            {session ? (
              <div className="ml-2 flex items-center gap-2 border-l border-slate-200 pl-3">
                <span className="hidden text-xs text-slate-500 sm:inline">
                  {session.display_name}
                </span>
                <button
                  type="button"
                  onClick={signOut}
                  className="rounded-lg px-2.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
                >
                  Sign out
                </button>
              </div>
            ) : null}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <Routes>
          <Route path="/" element={<Submit />} />
          <Route path="/ticket" element={<TicketStatus />} />
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <AdminOnly>
                <Dashboard />
              </AdminOnly>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
