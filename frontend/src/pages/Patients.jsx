import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Empty, ErrorBox, Spinner } from "../components/ui";

export default function Patients() {
  const nav = useNavigate();
  const fileRef = useRef();
  const [data, setData] = useState(null);
  const [q, setQ] = useState("");
  const [gender, setGender] = useState("");
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => {
      api(`/api/patients?q=${encodeURIComponent(q)}&gender=${gender}`).then(setData).catch(setError);
    }, 200);
    return () => clearTimeout(t);
  }, [q, gender, reload]);

  const importFhir = async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api("/api/patients/import/fhir", { method: "POST", form: fd });
      setNotice(`FHIR import complete: ${r.created.length} created, ${r.updated.length} updated.`);
      setReload((x) => x + 1);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Patients</h1>
          <p className="muted">Electronic health records available for trial screening</p>
        </div>
        <div className="btn-row">
          <input ref={fileRef} type="file" accept=".json,application/json" hidden onChange={importFhir} />
          <button className="btn ghost" onClick={() => fileRef.current.click()} disabled={busy}>
            {busy ? <Spinner label="Importing" /> : "Import FHIR bundle"}
          </button>
          <Link className="btn primary" to="/patients/new">+ Add patient</Link>
        </div>
      </div>
      <div className="filter-bar">
        <input className="search" placeholder="Search name, MRN, diagnosis or notes…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={gender} onChange={(e) => setGender(e.target.value)}>
          <option value="">All sexes</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
        </select>
      </div>
      {notice && <div className="alert success">{notice}</div>}
      <ErrorBox error={error} />
      {data && data.items.length === 0 && <Empty title="No patients found" />}
      {data && data.items.length > 0 && (
        <div className="card flush">
          <div className="table-wrap">
            <table className="hover">
              <thead><tr><th>Patient</th><th>MRN</th><th>Age</th><th>Sex</th><th>Diagnoses</th><th>Medications</th><th>Source</th></tr></thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id} className="clickable" onClick={() => nav(`/patients/${p.id}`)}>
                    <td><b>{p.name}</b></td>
                    <td className="mono small">{p.mrn}</td>
                    <td>{p.age ?? "—"}</td>
                    <td className="cap">{p.gender}</td>
                    <td className="small clamp-cell">{p.diagnoses.join(", ") || "—"}</td>
                    <td className="small clamp-cell muted">{p.medications.join(", ") || "—"}</td>
                    <td><span className="tag">{p.source}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="table-foot muted small">{data.total} patients</div>
        </div>
      )}
    </div>
  );
}
