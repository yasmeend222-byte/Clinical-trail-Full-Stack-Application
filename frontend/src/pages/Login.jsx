import { useState } from "react";
import { useAuth } from "../auth";
import { ErrorBox, Spinner } from "../components/ui";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "admin@contextsync.dev", password: "admin123", role: "Clinical Trial Coordinator" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-hero">
        <div className="brand-mark big">
          <svg viewBox="0 0 32 32" width="56" height="56"><rect width="32" height="32" rx="8" fill="#14b8a6" />
            <path d="M7 16h4l2.5-6 4 12 2.5-6H25" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </div>
        <h1>ContextSync</h1>
        <p className="lead">AI-powered clinical trial patient matching</p>
        <ul className="hero-points">
          <li>NLP extraction of inclusion &amp; exclusion criteria</li>
          <li>Structured + unstructured EHR analysis (FHIR ready)</li>
          <li>Ranked candidates with confidence scores</li>
          <li>Explainable decisions &amp; missing-test detection</li>
        </ul>
      </div>
      <form className="login-card" onSubmit={submit}>
        <h2>{mode === "login" ? "Sign in" : "Create account"}</h2>
        {mode === "register" && (
          <>
            <label>Full name<input value={form.name} onChange={set("name")} required /></label>
            <label>Role
              <select value={form.role} onChange={set("role")}>
                <option>Clinical Trial Coordinator</option>
                <option>Principal Investigator</option>
                <option>Research Nurse</option>
                <option>Data Manager</option>
              </select>
            </label>
          </>
        )}
        <label>Email<input type="email" value={form.email} onChange={set("email")} required /></label>
        <label>Password<input type="password" value={form.password} onChange={set("password")} required minLength={6} /></label>
        <ErrorBox error={error} />
        <button className="btn primary full" disabled={busy}>{busy ? <Spinner /> : mode === "login" ? "Sign in" : "Register"}</button>
        <div className="muted small center">
          {mode === "login" ? (
            <>New here? <button type="button" className="link" onClick={() => setMode("register")}>Create an account</button></>
          ) : (
            <>Have an account? <button type="button" className="link" onClick={() => setMode("login")}>Sign in</button></>
          )}
        </div>
        {mode === "login" && <div className="hint">Demo: admin@contextsync.dev / admin123</div>}
      </form>
    </div>
  );
}
