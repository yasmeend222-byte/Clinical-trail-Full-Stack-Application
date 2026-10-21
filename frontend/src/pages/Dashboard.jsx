import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api";
import { Badge, ErrorBox, StatCard } from "../components/ui";

function Distribution({ byStatus }) {
  const total = Object.values(byStatus).reduce((a, b) => a + b, 0);
  if (!total) return <div className="muted small">No matching runs yet — open a trial and run AI matching.</div>;
  const parts = [
    ["eligible", "Eligible", "var(--green)"],
    ["potentially_eligible", "Needs review", "var(--amber)"],
    ["ineligible", "Not eligible", "var(--red-soft)"],
  ];
  return (
    <div>
      <div className="dist-bar">
        {parts.map(([k, , c]) => byStatus[k] > 0 && (
          <div key={k} style={{ flex: byStatus[k], background: c }} title={`${byStatus[k]}`} />
        ))}
      </div>
      <div className="legend">
        {parts.map(([k, label, c]) => (
          <span key={k}><i style={{ background: c }} />{label} <b>{byStatus[k]}</b></span>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [d, setD] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => { api("/api/dashboard").then(setD).catch(setError); }, []);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Recruitment overview across all clinical trials</p>
        </div>
        <div className="btn-row">
          <Link className="btn ghost" to="/patients/new">Add patient</Link>
          <Link className="btn primary" to="/trials/new">+ New trial</Link>
        </div>
      </div>
      <ErrorBox error={error} />
      {d && (
        <>
          <div className="stats">
            <StatCard label="Patients in registry" value={d.patients} />
            <StatCard label="Clinical trials" value={d.trials} hint={`${d.recruiting_trials} recruiting`} />
            <StatCard label="Eligible candidates" value={d.by_status.eligible} tone="green" />
            <StatCard label="Need review" value={d.by_status.potentially_eligible} tone="amber" />
            <StatCard label="Approved by coordinators" value={(d.by_review.approved || 0) + (d.by_review.enrolled || 0)} />
          </div>

          <div className="grid-2">
            <div className="card">
              <h3>Eligibility distribution</h3>
              <Distribution byStatus={d.by_status} />
            </div>
            <div className="card">
              <h3>AI pipeline</h3>
              <dl className="kv">
                <dt>Criteria extraction</dt><dd>Rule-based clinical NLP + medical vocabulary</dd>
                <dt>Semantic search</dt><dd>{d.system.embedding}</dd>
                <dt>Explanations</dt>
                <dd>{d.system.llm_enabled ? <>LLM · <code>{d.system.llm_model}</code></> : "Template (configure LLM_BASE_URL for Llama/GPT)"}</dd>
                <dt>Database</dt><dd>{d.system.database}</dd>
              </dl>
            </div>
          </div>

          <div className="card">
            <div className="section-head"><h3>Trials</h3><Link to="/trials" className="small">View all →</Link></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Trial</th><th>Condition</th><th>Phase</th><th>Status</th><th className="num">Eligible</th><th className="num">Review</th><th className="num">Not eligible</th><th>Last matched</th></tr></thead>
                <tbody>
                  {d.trials_overview.map((t) => (
                    <tr key={t.id}>
                      <td><Link to={`/trials/${t.id}`}><b>{t.trial_code}</b></Link><div className="muted small clamp">{t.title}</div></td>
                      <td>{t.condition}</td>
                      <td>{t.phase}</td>
                      <td><Badge status={t.status} /></td>
                      <td className="num green-text">{t.match_counts.eligible}</td>
                      <td className="num amber-text">{t.match_counts.potentially_eligible}</td>
                      <td className="num muted">{t.match_counts.ineligible}</td>
                      <td className="small muted">{t.last_matched_at ? fmtDate(t.last_matched_at) : "never"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h3>Recent activity (audit log)</h3>
            {d.activity.length === 0 && <div className="muted small">No activity yet.</div>}
            <ul className="activity">
              {d.activity.map((a, i) => (
                <li key={i}><code>{a.action}</code> <span>{a.detail}</span> <span className="muted small">— {a.by || "system"}, {fmtDate(a.at)}</span></li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
