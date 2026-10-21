import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Badge, Empty, ErrorBox } from "../components/ui";

export default function Trials() {
  const [trials, setTrials] = useState(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      api(`/api/trials?q=${encodeURIComponent(q)}`).then(setTrials).catch(setError);
    }, 200);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Clinical Trials</h1>
          <p className="muted">Upload protocols, review extracted criteria and run patient matching</p>
        </div>
        <Link className="btn primary" to="/trials/new">+ New trial</Link>
      </div>
      <input className="search" placeholder="Search by title, condition or code…" value={q} onChange={(e) => setQ(e.target.value)} />
      <ErrorBox error={error} />
      {trials && trials.length === 0 && <Empty title="No trials found">Create a trial by pasting or uploading a protocol.</Empty>}
      <div className="trial-grid">
        {trials?.map((t) => (
          <Link key={t.id} to={`/trials/${t.id}`} className="trial-card">
            <div className="trial-card-top">
              <span className="code">{t.trial_code}</span>
              <Badge status={t.status} />
            </div>
            <h3>{t.title}</h3>
            <div className="muted small">{[t.phase, t.condition, t.sponsor].filter(Boolean).join(" · ")}</div>
            <div className="trial-card-foot">
              <span className="small">{t.inclusion_count} inclusion · {t.exclusion_count} exclusion</span>
              <span className="counts">
                <span className="pill green" title="Eligible">{t.match_counts.eligible}</span>
                <span className="pill amber" title="Needs review">{t.match_counts.potentially_eligible}</span>
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
