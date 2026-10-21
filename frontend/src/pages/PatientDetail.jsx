import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, downloadJson } from "../api";
import MatchDrawer from "../components/MatchDrawer";
import { Badge, Empty, ErrorBox, ScoreBar, Spinner } from "../components/ui";

export default function PatientDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState(null);
  const [matches, setMatches] = useState([]);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api(`/api/patients/${id}`), api(`/api/patients/${id}/matches`)])
      .then(([pt, m]) => { setP(pt); setMatches(m); })
      .catch(setError);
  }, [id]);

  const run = async (label, fn) => {
    setBusy(label);
    setError(null);
    try { await fn(); } catch (e) { setError(e); } finally { setBusy(""); }
  };

  const findTrials = () => run("match", async () => setMatches(await api(`/api/patients/${id}/match`, { method: "POST" })));
  const exportFhir = () => run("fhir", async () => downloadJson(await api(`/api/patients/${id}/fhir`), `${p.mrn}-fhir.json`));
  const remove = () => run("delete", async () => { await api(`/api/patients/${id}`, { method: "DELETE" }); nav("/patients"); });

  if (!p) return <div className="page"><ErrorBox error={error} />{!error && <Spinner label="Loading patient" />}</div>;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">{p.mrn} · source: {p.source}</div>
          <h1>{p.name}</h1>
          <div className="meta-row">
            <span>{p.age ?? "?"} years</span>
            <span className="cap">{p.gender}</span>
            {p.birth_date && <span className="muted small">DOB {p.birth_date}</span>}
            {p.demographics?.city && <span className="muted small">{p.demographics.city}{p.demographics.country ? `, ${p.demographics.country}` : ""}</span>}
          </div>
        </div>
        <div className="btn-row">
          <button className="btn ghost" onClick={exportFhir} disabled={!!busy}>Export FHIR</button>
          <Link className="btn ghost" to={`/patients/${id}/edit`}>Edit</Link>
          <button className="btn primary" onClick={findTrials} disabled={!!busy}>
            {busy === "match" ? <Spinner label="Matching…" /> : "▶ Find matching trials"}
          </button>
        </div>
      </div>
      <ErrorBox error={error} />

      <div className="grid-2">
        <div className="card">
          <h3>Diagnoses</h3>
          {p.diagnoses.length ? <div className="chips">{p.diagnoses.map((d) => <span key={d} className="chip condition">{d}</span>)}</div> : <div className="muted small">None recorded</div>}
          <h3 className="mt">Medications</h3>
          {p.medications.length ? <div className="chips">{p.medications.map((d) => <span key={d} className="chip medication">{d}</span>)}</div> : <div className="muted small">None recorded</div>}
        </div>
        <div className="card">
          <h3>Lab results</h3>
          {p.lab_results.length === 0 ? <div className="muted small">No lab results</div> : (
            <table className="compact">
              <thead><tr><th>Test</th><th className="num">Value</th><th>Unit</th><th>Date</th></tr></thead>
              <tbody>
                {p.lab_results.map((l, i) => (
                  <tr key={i}><td>{l.name}</td><td className="num"><b>{l.value}</b></td><td className="muted">{l.unit}</td><td className="muted small">{l.date}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="grid-2">
        <div className="card"><h3>Medical history</h3><p className="prewrap">{p.medical_history || <span className="muted">—</span>}</p></div>
        <div className="card"><h3>Clinical notes</h3><p className="prewrap">{p.clinical_notes || <span className="muted">—</span>}</p></div>
      </div>

      <div className="card flush">
        <div className="section-head pad"><h3>Trial matches (personalized)</h3></div>
        {matches.length === 0 ? (
          <Empty title="Not screened yet">Click <b>Find matching trials</b> to evaluate this patient against all recruiting trials.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="hover">
              <thead><tr><th>Trial</th><th>Status</th><th style={{ width: 170 }}>Confidence</th><th>Missing tests</th><th>Review</th></tr></thead>
              <tbody>
                {matches.map((m) => (
                  <tr key={m.id} className="clickable" onClick={() => setSelected(m.id)}>
                    <td><b>{m.trial_code}</b><div className="muted small clamp">{m.trial_title}</div></td>
                    <td><Badge status={m.eligibility_status} /></td>
                    <td><ScoreBar value={m.confidence_score} /></td>
                    <td className="small">{m.missing_tests.map((t) => t.test).join(", ") || <span className="muted">—</span>}</td>
                    <td><Badge status={m.review_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="danger-zone">
        {confirmDelete ? (
          <>
            <span>Permanently delete this patient record?</span>
            <button className="btn danger small" onClick={remove} disabled={!!busy}>Yes, delete</button>
            <button className="btn ghost small" onClick={() => setConfirmDelete(false)}>Cancel</button>
          </>
        ) : (
          <button className="btn danger-outline small" onClick={() => setConfirmDelete(true)}>Delete patient</button>
        )}
      </div>

      <MatchDrawer matchId={selected} context="patient" onClose={() => setSelected(null)}
        onChange={(d) => setMatches((ms) => ms.map((m) => (m.id === d.id ? { ...m, review_status: d.review_status } : m)))} />
    </div>
  );
}
