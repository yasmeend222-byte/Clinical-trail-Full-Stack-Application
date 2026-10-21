import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, Spinner } from "../components/ui";

const EMPTY = {
  mrn: "", name: "", birth_date: "", gender: "female", city: "",
  diagnoses: "", medications: "", medical_history: "", clinical_notes: "",
  lab_results: [{ name: "", value: "", unit: "", date: "" }],
};
const LAB_SUGGESTIONS = ["HbA1c", "eGFR", "BMI", "LVEF", "NT-proBNP", "Systolic blood pressure", "LDL cholesterol",
  "Blood eosinophil count", "FEV1 % predicted", "ECOG performance status", "Absolute neutrophil count", "Platelet count",
  "ALT", "AST", "Serum creatinine", "Hemoglobin"];

const lines = (s) => s.split(/\n|;/).map((x) => x.trim()).filter(Boolean);

export default function PatientForm() {
  const { id } = useParams();
  const nav = useNavigate();
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;
    api(`/api/patients/${id}`).then((p) => setF({
      mrn: p.mrn, name: p.name, birth_date: p.birth_date || "", gender: p.gender, city: p.demographics?.city || "",
      diagnoses: p.diagnoses.join("\n"), medications: p.medications.join("\n"),
      medical_history: p.medical_history, clinical_notes: p.clinical_notes,
      lab_results: p.lab_results.length ? p.lab_results.map((l) => ({ ...l, value: String(l.value) })) : EMPTY.lab_results,
      demographics: p.demographics,
    })).catch(setError);
  }, [id]);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const setLab = (i, k) => (e) => setF({ ...f, lab_results: f.lab_results.map((l, j) => (j === i ? { ...l, [k]: e.target.value } : l)) });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body = {
      mrn: f.mrn, name: f.name, birth_date: f.birth_date || null, gender: f.gender,
      demographics: { ...(f.demographics || {}), city: f.city || undefined },
      diagnoses: lines(f.diagnoses), medications: lines(f.medications),
      lab_results: f.lab_results.filter((l) => l.name && l.value !== "").map((l) => ({ ...l, value: Number(l.value) })),
      medical_history: f.medical_history, clinical_notes: f.clinical_notes,
    };
    try {
      const p = await api(id ? `/api/patients/${id}` : "/api/patients", { method: id ? "PUT" : "POST", body });
      nav(`/patients/${p.id}`);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{id ? "Edit patient" : "Add patient"}</h1>
          <p className="muted">Structured fields plus free-text notes — both are analysed during matching</p>
        </div>
      </div>
      <form className="card form" onSubmit={submit}>
        <div className="form-grid">
          <label>MRN *<input value={f.mrn} onChange={set("mrn")} required /></label>
          <label>Full name *<input value={f.name} onChange={set("name")} required /></label>
          <label>Date of birth<input type="date" value={f.birth_date} onChange={set("birth_date")} /></label>
          <label>Sex
            <select value={f.gender} onChange={set("gender")}>
              <option value="female">Female</option><option value="male">Male</option>
              <option value="other">Other</option><option value="unknown">Unknown</option>
            </select>
          </label>
          <label>City<input value={f.city} onChange={set("city")} /></label>
          <span />
          <label>Diagnoses <span className="muted tiny">(one per line)</span><textarea rows={4} value={f.diagnoses} onChange={set("diagnoses")} placeholder={"Type 2 diabetes mellitus\nHypertension"} /></label>
          <label>Medications <span className="muted tiny">(one per line)</span><textarea rows={4} value={f.medications} onChange={set("medications")} placeholder={"Metformin 1000 mg BID"} /></label>
        </div>

        <h3>Lab results</h3>
        <datalist id="lab-names">{LAB_SUGGESTIONS.map((l) => <option key={l} value={l} />)}</datalist>
        <div className="lab-rows">
          {f.lab_results.map((l, i) => (
            <div key={i} className="lab-row">
              <input list="lab-names" placeholder="Test (e.g. HbA1c)" value={l.name} onChange={setLab(i, "name")} />
              <input type="number" step="any" placeholder="Value" value={l.value} onChange={setLab(i, "value")} />
              <input placeholder="Unit" value={l.unit} onChange={setLab(i, "unit")} />
              <input type="date" value={l.date} onChange={setLab(i, "date")} />
              <button type="button" className="icon-btn" onClick={() => setF({ ...f, lab_results: f.lab_results.filter((_, j) => j !== i) })}>✕</button>
            </div>
          ))}
          <button type="button" className="btn ghost small" onClick={() => setF({ ...f, lab_results: [...f.lab_results, { name: "", value: "", unit: "", date: "" }] })}>+ Add lab</button>
        </div>

        <div className="form-grid">
          <label>Medical history<textarea rows={4} value={f.medical_history} onChange={set("medical_history")} /></label>
          <label>Clinical notes<textarea rows={4} value={f.clinical_notes} onChange={set("clinical_notes")} placeholder="Free-text notes. Negations like “denies chest pain” or “no history of stroke” are understood." /></label>
        </div>
        <ErrorBox error={error} />
        <div className="btn-row">
          <button type="button" className="btn ghost" onClick={() => nav(-1)}>Cancel</button>
          <button className="btn primary" disabled={busy}>{busy ? <Spinner label="Saving" /> : "Save patient"}</button>
        </div>
      </form>
    </div>
  );
}
