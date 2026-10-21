import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, fmtDate } from "../api";
import CriteriaList from "../components/CriteriaList";
import MatchDrawer from "../components/MatchDrawer";
import { Badge, Empty, ErrorBox, ScoreBar, Spinner, StatCard } from "../components/ui";

const FILTERS = [
  ["", "All"],
  ["eligible", "Eligible"],
  ["potentially_eligible", "Needs review"],
  ["ineligible", "Not eligible"],
];

export default function TrialDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [trial, setTrial] = useState(null);
  const [matches, setMatches] = useState([]);
  const [tab, setTab] = useState("candidates");
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState(null);
  const [newCrit, setNewCrit] = useState({ type: "inclusion", description: "" });

  const load = useCallback(async () => {
    try {
      const [t, m] = await Promise.all([api(`/api/trials/${id}`), api(`/api/trials/${id}/matches`)]);
      setTrial(t);
      setMatches(m);
    } catch (e) {
      setError(e);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const run = async (label, fn) => {
    setBusy(label);
    setError(null);
    try { await fn(); } catch (e) { setError(e); } finally { setBusy(""); }
  };

  const runMatching = () => run("match", async () => {
    const m = await api(`/api/trials/${id}/match`, { method: "POST" });
    setMatches(m);
    setTab("candidates");
    setTrial(await api(`/api/trials/${id}`));
  });

  const setStatus = (status) => run("status", async () => {
    setTrial(await api(`/api/trials/${id}`, { method: "PUT", body: { status } }));
  });

  const remove = () => run("delete", async () => {
    await api(`/api/trials/${id}`, { method: "DELETE" });
    nav("/trials");
  });

  const addCriterion = (e) => {
    e.preventDefault();
    run("crit", async () => {
      await api(`/api/trials/${id}/criteria`, { method: "POST", body: newCrit });
      setNewCrit({ ...newCrit, description: "" });
      setTrial(await api(`/api/trials/${id}`));
    });
  };

  const deleteCriterion = (c) => run("crit", async () => {
    await api(`/api/trials/${id}/criteria/${c.id}`, { method: "DELETE" });
    setTrial(await api(`/api/trials/${id}`));
  });

  if (!trial) return <div className="page"><ErrorBox error={error} />{!error && <Spinner label="Loading trial" />}</div>;

  const counts = { eligible: 0, potentially_eligible: 0, ineligible: 0 };
  matches.forEach((m) => { counts[m.eligibility_status] += 1; });
  const shown = filter ? matches.filter((m) => m.eligibility_status === filter) : matches;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">{trial.trial_code} · {trial.phase} · {trial.condition}</div>
          <h1 className="title-lg">{trial.title}</h1>
          {trial.description && <p className="muted">{trial.description}</p>}
          <div className="meta-row">
            <Badge status={trial.status} />
            {trial.sponsor && <span className="muted small">Sponsor: {trial.sponsor}</span>}
            <span className="muted small">Last matched: {trial.last_matched_at ? fmtDate(trial.last_matched_at) : "never"}</span>
          </div>
        </div>
        <div className="btn-col">
          <button className="btn primary" onClick={runMatching} disabled={!!busy}>
            {busy === "match" ? <Spinner label="Matching patients…" /> : "▶ Run AI matching"}
          </button>
          <select value={trial.status} onChange={(e) => setStatus(e.target.value)} className="small-select">
            <option value="recruiting">Recruiting</option>
            <option value="draft">Draft</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>
      <ErrorBox error={error} />

      <div className="stats">
        <StatCard label="Patients screened" value={matches.length} />
        <StatCard label="Eligible" value={counts.eligible} tone="green" />
        <StatCard label="Needs review" value={counts.potentially_eligible} tone="amber" />
        <StatCard label="Not eligible" value={counts.ineligible} />
        <StatCard label="Criteria" value={trial.criteria.length} hint={`${trial.inclusion_count} incl · ${trial.exclusion_count} excl`} />
      </div>

      <div className="tabs">
        {[["candidates", "Ranked candidates"], ["criteria", "Eligibility criteria"], ["protocol", "Protocol text"]].map(([k, l]) => (
          <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>

      {tab === "candidates" && (
        <div className="card flush">
          <div className="filter-row">
            {FILTERS.map(([k, l]) => (
              <button key={k} className={`chip-btn ${filter === k ? "active" : ""}`} onClick={() => setFilter(k)}>
                {l} {k ? `(${counts[k]})` : `(${matches.length})`}
              </button>
            ))}
          </div>
          {matches.length === 0 ? (
            <Empty title="No candidates yet">Click <b>Run AI matching</b> to screen every patient in the registry against this trial.</Empty>
          ) : (
            <div className="table-wrap">
              <table className="hover">
                <thead>
                  <tr><th>#</th><th>Patient</th><th>Age / Sex</th><th>Status</th><th style={{ width: 170 }}>Confidence</th><th>Criteria</th><th>Missing tests</th><th>Review</th></tr>
                </thead>
                <tbody>
                  {shown.map((m, i) => (
                    <tr key={m.id} onClick={() => setSelected(m.id)} className="clickable">
                      <td className="muted">{i + 1}</td>
                      <td><b>{m.patient.name}</b><div className="muted small">{m.patient.mrn}</div></td>
                      <td>{m.patient.age ?? "?"} / {m.patient.gender[0]?.toUpperCase()}</td>
                      <td><Badge status={m.eligibility_status} /></td>
                      <td><ScoreBar value={m.confidence_score} /></td>
                      <td className="nowrap">
                        <span className="pill green">{m.matched_count}</span>{" "}
                        <span className="pill red">{m.unmet_count}</span>{" "}
                        <span className="pill amber">{m.unknown_count}</span>
                      </td>
                      <td className="small">{m.missing_tests.map((t) => t.test).join(", ") || <span className="muted">—</span>}</td>
                      <td><Badge status={m.review_status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "criteria" && (
        <div className="card">
          <CriteriaList criteria={trial.criteria} onDelete={deleteCriterion} />
          <form className="add-crit" onSubmit={addCriterion}>
            <select value={newCrit.type} onChange={(e) => setNewCrit({ ...newCrit, type: e.target.value })}>
              <option value="inclusion">Inclusion</option>
              <option value="exclusion">Exclusion</option>
            </select>
            <input placeholder="Add a criterion, e.g. “HbA1c >= 7.5%” or “History of stroke”" value={newCrit.description}
              onChange={(e) => setNewCrit({ ...newCrit, description: e.target.value })} minLength={3} required />
            <button className="btn ghost" disabled={!!busy}>Add</button>
          </form>
          <p className="muted small">Changing criteria does not update existing results — re-run matching afterwards.</p>
        </div>
      )}

      {tab === "protocol" && (
        <div className="card">
          <pre className="protocol">{trial.protocol_text}</pre>
          <div className="danger-zone">
            {confirmDelete ? (
              <>
                <span>Delete this trial and all its match results?</span>
                <button className="btn danger small" onClick={remove} disabled={!!busy}>Yes, delete</button>
                <button className="btn ghost small" onClick={() => setConfirmDelete(false)}>Cancel</button>
              </>
            ) : (
              <button className="btn danger-outline small" onClick={() => setConfirmDelete(true)}>Delete trial</button>
            )}
          </div>
        </div>
      )}

      <MatchDrawer matchId={selected} onClose={() => setSelected(null)}
        onChange={(d) => setMatches((ms) => ms.map((m) => (m.id === d.id ? { ...m, review_status: d.review_status } : m)))} />
    </div>
  );
}
