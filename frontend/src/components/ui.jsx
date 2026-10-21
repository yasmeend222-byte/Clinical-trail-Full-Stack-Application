const STATUS = {
  eligible: ["Eligible", "green"],
  potentially_eligible: ["Needs review", "amber"],
  ineligible: ["Not eligible", "red"],
  met: ["Met", "green"],
  not_met: ["Not met", "red"],
  unknown: ["Unknown", "amber"],
  pending: ["Pending", "gray"],
  approved: ["Approved", "green"],
  rejected: ["Rejected", "red"],
  contacted: ["Contacted", "blue"],
  enrolled: ["Enrolled", "teal"],
  recruiting: ["Recruiting", "green"],
  closed: ["Closed", "gray"],
  draft: ["Draft", "gray"],
};

export function Badge({ status, children }) {
  const [label, color] = STATUS[status] || [status, "gray"];
  return <span className={`badge ${color}`}>{children || label}</span>;
}

export function ScoreBar({ value }) {
  const v = Math.max(0, Math.min(100, value || 0));
  const color = v >= 75 ? "var(--green)" : v >= 50 ? "var(--amber)" : "var(--red)";
  return (
    <div className="score">
      <div className="score-track"><div className="score-fill" style={{ width: `${v}%`, background: color }} /></div>
      <span className="score-num">{v.toFixed(0)}%</span>
    </div>
  );
}

export function Spinner({ label }) {
  return <span className="spinner-wrap"><span className="spinner" />{label}</span>;
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return <div className="alert error">{String(error.message || error)}</div>;
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <div className="empty-title">{title}</div>
      {children && <div className="muted">{children}</div>}
    </div>
  );
}

export function StatCard({ label, value, hint, tone }) {
  return (
    <div className={`stat ${tone || ""}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value ?? "—"}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}
