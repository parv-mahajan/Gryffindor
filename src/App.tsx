import { useEffect, useState } from "react";
import "./App.css";

type Complaint = {
  id: number;
  title: string;
  category: string;
  location: string;
  priority: "High" | "Medium" | "Low";
  status: "Pending" | "In Progress" | "Resolved";
};

const initialComplaints: Complaint[] = [
  { id: 101, title: "Large pothole near main gate", category: "Roads", location: "Zone A", priority: "High", status: "Pending" },
  { id: 102, title: "Garbage not collected", category: "Sanitation", location: "Zone B", priority: "Medium", status: "In Progress" },
  { id: 103, title: "Streetlight not working", category: "Electricity", location: "Zone C", priority: "Medium", status: "Pending" },
  { id: 104, title: "Water leakage on main road", category: "Water", location: "Zone A", priority: "High", status: "Resolved" },
];

const STORAGE_KEY = "civicsense_complaints";
function findDuplicate(
  title: string,
  location: string,
  complaints: Complaint[]
): Complaint | undefined {
  const normalize = (value: string) =>
    value.toLowerCase().replace(/[^a-z0-9\s]/g, "").replace(/\s+/g, " ").trim();

  const newTitle = normalize(title);
  const newLocation = normalize(location);

  return complaints.find((complaint) => {
    const existingTitle = normalize(complaint.title);
    const existingLocation = normalize(complaint.location);

    const sameLocation = existingLocation === newLocation;
    const sameTitle =
      existingTitle === newTitle ||
      existingTitle.includes(newTitle) ||
      newTitle.includes(existingTitle);

    return sameLocation && sameTitle;
  });
}

function loadComplaints(): Complaint[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed: unknown = JSON.parse(saved);
      if (Array.isArray(parsed)) return parsed as Complaint[];
    }
  } catch (error) {
    console.error("Could not load complaints:", error);
  }
  return initialComplaints;
}

function App() {
  const [complaints, setComplaints] = useState<Complaint[]>(loadComplaints);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [category, setCategory] = useState("Roads");
  const [filter, setFilter] = useState("All");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(complaints));
    } catch (error) {
      console.error("Could not save complaints:", error);
    }
  }, [complaints]);

  const pending = complaints.filter((c) => c.status === "Pending").length;
  const progress = complaints.filter((c) => c.status === "In Progress").length;
  const resolved = complaints.filter((c) => c.status === "Resolved").length;
  const highPriority = complaints.filter(
    (c) => c.priority === "High" && c.status !== "Resolved"
  ).length;

  const filtered = complaints.filter(
    (c) => filter === "All" || c.status === filter
  );

  function submitComplaint(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!title.trim() || !location.trim()) {
      setNotice("Please enter the issue description and location.");
      return;
    }

    const duplicate = findDuplicate(title, location, complaints);

if (duplicate) {
  const continueAnyway = window.confirm(
    `Possible duplicate found!\n\nExisting complaint: ${duplicate.title}\nLocation: ${duplicate.location}\nStatus: ${duplicate.status}\n\nSubmit this complaint anyway?`
  );

  if (!continueAnyway) {
    setNotice("Possible duplicate detected. No new complaint was added.");
    return;
  }
}
    const text = title.toLowerCase();

    const detectedCategory =
      text.includes("garbage") || text.includes("waste") || text.includes("trash")
        ? "Sanitation"
        : text.includes("water") || text.includes("leak")
        ? "Water"
        : text.includes("light") || text.includes("electric")
        ? "Electricity"
        : text.includes("pothole") || text.includes("road")
        ? "Roads"
        : category;

    const newComplaint: Complaint = {
      id: Date.now(),
      title: title.trim(),
      category: detectedCategory,
      location: location.trim(),
      priority:
        text.includes("accident") ||
        text.includes("danger") ||
        text.includes("leak") ||
        text.includes("emergency")
          ? "High"
          : "Medium",
      status: "Pending",
    };

    setComplaints((previous) => [newComplaint, ...previous]);
    setTitle("");
    setLocation("");
    setCategory("Roads");
    setShowForm(false);
    setFilter("All");
    setNotice("Complaint submitted successfully!");
  }

  function updateStatus(id: number, status: Complaint["status"]) {
    setComplaints((previous) =>
      previous.map((c) => (c.id === id ? { ...c, status } : c))
    );
    setNotice("Complaint status updated.");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">C</div>
          <div>
            <strong>CivicSense</strong>
            <small>CIVIC INTELLIGENCE</small>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <div className="nav-item active">▦ <span>Overview</span></div>
        <div className="nav-item">◎ <span>Complaints</span></div>
        <div className="nav-item">⌖ <span>Area Insights</span></div>
        <div className="nav-item">◈ <span>AI Intelligence</span></div>

        <div className="sidebar-bottom">
          <div className="online-dot" /> System online
          <p>Hackathon MVP · PS 02</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div><span className="breadcrumb">Workspace /</span> Overview</div>
          <div className="admin-chip"><span>●</span> Admin Dashboard</div>
        </header>

        <section className="welcome">
          <div>
            <div className="eyebrow">CIVIC OPERATIONS CENTER</div>
            <h1>Good morning, Admin <span>✳</span></h1>
            <p>Turn citizen reports into smarter, faster civic action.</p>
          </div>
          <button className="primary-btn" onClick={() => { setShowForm(!showForm); setNotice(""); }}>
            + Report an issue
          </button>
        </section>

        {notice && <div className="notice">{notice}</div>}

        {showForm && (
          <form className="complaint-form" onSubmit={submitComplaint}>
            <h2>Submit a civic complaint</h2>
            <label>
              Issue description
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Large pothole causing accidents" required />
            </label>
            <div className="form-grid">
              <label>
                Location / area
                <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Zone A, Main Road" required />
              </label>
              <label>
                Issue category
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option>Roads</option>
                  <option>Sanitation</option>
                  <option>Water</option>
                  <option>Electricity</option>
                  <option>Other</option>
                </select>
              </label>
            </div>
            <div className="form-actions">
              <button type="button" className="secondary-btn" onClick={() => setShowForm(false)}>Cancel</button>
              <button className="primary-btn" type="submit">Submit complaint</button>
            </div>
          </form>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-top"><span>Total complaints</span><span className="stat-icon">▤</span></div>
            <strong>{complaints.length}</strong>
            <small>Reports in the system</small>
          </div>
          <div className="stat-card">
            <div className="stat-top"><span>Pending review</span><span className="stat-icon amber">◷</span></div>
            <strong>{pending}</strong>
            <small>Awaiting action</small>
          </div>
          <div className="stat-card">
            <div className="stat-top"><span>In progress</span><span className="stat-icon blue">↗</span></div>
            <strong>{progress}</strong>
            <small>Being addressed</small>
          </div>
          <div className="stat-card">
            <div className="stat-top"><span>Resolved</span><span className="stat-icon green">✓</span></div>
            <strong>{resolved}</strong>
            <small>Marked as resolved</small>
          </div>
        </section>

        <section className="content-grid">
          <div className="panel complaints-panel">
            <div className="panel-heading">
              <div><h2>Recent complaints</h2><p>Review reports and update their status.</p></div>
              <select className="filter-select" value={filter} onChange={(e) => setFilter(e.target.value)}>
                <option>All</option>
                <option>Pending</option>
                <option>In Progress</option>
                <option>Resolved</option>
              </select>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>COMPLAINT</th><th>PRIORITY</th><th>STATUS</th></tr></thead>
                <tbody>
                  {filtered.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <strong>{c.title}</strong>
                        <small>{c.category} · {c.location} · #{String(c.id).slice(-5)}</small>
                      </td>
                      <td><span className={`priority ${c.priority.toLowerCase()}`}>{c.priority}</span></td>
                      <td>
                        <select
                          className="status-select"
                          value={c.status}
                          aria-label={`Status for ${c.title}`}
                          onChange={(e) => updateStatus(c.id, e.target.value as Complaint["status"])}
                        >
                          <option>Pending</option>
                          <option>In Progress</option>
                          <option>Resolved</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length === 0 && <p className="empty-state">No complaints in this category.</p>}
            </div>
          </div>

          <div className="panel insights-panel">
            <div className="panel-heading">
              <div><h2>AI insights</h2><p>Decision support overview</p></div>
              <span className="ai-mark">✳</span>
            </div>
            <div className="insight-highlight">
              <span className="insight-tag">PRIORITY WATCH</span>
              <h3>{highPriority} high-priority issue(s)</h3>
              <p>Review safety-sensitive complaints first.</p>
            </div>
            <div className="insight-row">
              <span className="insight-symbol">⌕</span>
              <div><strong>Category detection</strong><p>Uses basic description keywords</p></div>
              <span className="mini-status">Demo</span>
            </div>
            <div className="insight-row">
              <span className="insight-symbol">⇄</span>
              <div><strong>Duplicate review</strong><p>Similarity engine not connected yet</p></div>
              <span className="mini-status muted">Pending</span>
            </div>
            <div className="insight-row">
              <span className="insight-symbol">⌖</span>
              <div><strong>Hotspot analysis</strong><p>Map analytics to be added next</p></div>
              <span className="mini-status muted">Pending</span>
            </div>
            <div className="honesty-note">
              Reports are saved in this browser. This is a prototype, not a shared database.
            </div>
          </div>
        </section>

        <footer>
          <span>© CivicSense · PS 02</span>
          <span>Built for smarter civic services</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
