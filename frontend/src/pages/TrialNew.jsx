import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import CriteriaList from "../components/CriteriaList";
import { ErrorBox, Spinner } from "../components/ui";

const SAMPLE = `Inclusion Criteria:
- Adults aged 40 to 80 years
- Diagnosis of hypertension
- Systolic blood pressure between 140 and 179 mmHg
- LDL cholesterol >= 100 mg/dL
- Currently taking a statin

Exclusion Criteria:
- History of stroke or myocardial infarction
- eGFR < 45 mL/min/1.73m2
- Pregnant or breastfeeding women
- Current treatment with an anticoagulant`;

export default function TrialNew() {
  const nav = useNavigate();
  const fileRef = useRef();
  const [form, setForm] = useState({ title: "", trial_code: "", phase: "Phase II", condition: "", sponsor: "", description: "", protocol_text: "", status: "recruiting" });
  const [criteria, setCriteria] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const run = async (label, fn) => {
    setBusy(label);
    setError(null);
    try { await fn(); } catch (e) { setError(e); } finally { setBusy(""); }
  };

  const preview = () => run("extract", async () => {
    const r = await api("/api/trials/extract-preview", { method: "POST", body: { protocol_text: form.protocol_text } });
    setCriteria(r.criteria);
  });

  const upload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    run("upload", async () => {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api("/api/trials/extract-file", { method: "POST", form: fd });
      setForm((f) => ({ ...f, protocol_text: r.protocol_text, title: f.title || file.name.replace(/\.[^.]+$/, "") }));
      setCriteria(r.criteria);
    });
    e.target.value = "";
  };

  const save = (e) => {
    e.preventDefault();
    run("save", async () => {
      const t = await api("/api/trials", { method: "POST", body: form });
      nav(`/trials/${t.id}`);
    });
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>New clinical trial</h1>
          <p className="muted">Paste or upload the protocol — eligibility criteria are extracted automatically with NLP</p>
        </div>
      </div>
      <form className="card form" onSubmit={save}>
        <div className="form-grid">
          <label className="span-2">Trial title *<input value={form.title} onChange={set("title")} required minLength={3} /></label>
          <label>Trial code<input value={form.trial_code} onChange={set("trial_code")} placeholder="auto-generated" /></label>
          <label>Phase
            <select value={form.phase} onChange={set("phase")}>
              {["Phase I", "Phase I/II", "Phase II", "Phase III", "Phase IV", "Observational"].map((p) => <option key={p}>{p}</option>)}
            </select>
          </label>
          <label>Condition<input value={form.condition} onChange={set("condition")} placeholder="e.g. Type 2 Diabetes" /></label>
          <label>Sponsor<input value={form.sponsor} onChange={set("sponsor")} /></label>
          <label className="span-2">Description<textarea rows={2} value={form.description} onChange={set("description")} /></label>
        </div>

        <div className="section-head">
          <h3>Protocol / eligibility text *</h3>
          <div className="btn-row">
            <button type="button" className="btn ghost small" onClick={() => setForm({ ...form, protocol_text: SAMPLE })}>Insert sample</button>
            <input ref={fileRef} type="file" accept=".pdf,.txt,.md" hidden onChange={upload} />
            <button type="button" className="btn ghost small" onClick={() => fileRef.current.click()} disabled={!!busy}>
              {busy === "upload" ? <Spinner label="Reading" /> : "Upload PDF / TXT"}
            </button>
          </div>
        </div>
        <textarea className="mono" rows={12} value={form.protocol_text} onChange={set("protocol_text")} required
          placeholder={"Inclusion Criteria:\n- ...\n\nExclusion Criteria:\n- ..."} />
        <ErrorBox error={error} />
        <div className="btn-row">
          <button type="button" className="btn ghost" onClick={preview} disabled={!!busy || form.protocol_text.length < 10}>
            {busy === "extract" ? <Spinner label="Extracting" /> : "Preview extracted criteria"}
          </button>
          <button className="btn primary" disabled={!!busy}>{busy === "save" ? <Spinner label="Saving" /> : "Save trial"}</button>
        </div>
      </form>

      {criteria && (
        <div className="card">
          <h3>Extracted criteria preview</h3>
          <p className="muted small">Each criterion is converted into structured checks (age, sex, diagnosis, lab thresholds, medications). Items that can't be structured are evaluated semantically against clinical notes.</p>
          <CriteriaList criteria={criteria} />
        </div>
      )}
    </div>
  );
}
