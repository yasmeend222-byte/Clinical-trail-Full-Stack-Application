# ContextSync: Clinical Trial Patient Matcher

AI-powered web application that matches patient health records against clinical trial eligibility criteria.
It extracts inclusion/exclusion criteria from protocols with NLP, evaluates structured and unstructured patient data,
ranks candidates by confidence, identifies missing diagnostic tests and explains every decision.

**Stack:** React.js (Vite/Node) · FastAPI (Python) · SQLAlchemy (SQLite or PostgreSQL) · HL7 FHIR R4 ·
rule-based clinical NLP · TF-IDF vector store · Llama/GPT (OpenAI-compatible API) for explanations.

## Quick start (Windows)

From Command Prompt:

```cmd
start.bat
```

The script creates the backend virtual environment and installs dependencies when needed, then opens the API and frontend in separate Command Prompt windows.

From PowerShell:

```powershell
./start.ps1
```

Or manually:

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in with **admin@contextsync.dev / admin123**.
API documentation (Swagger) is at http://127.0.0.1:8000/docs.

On first start the database is seeded with 4 trials (diabetes, HER2+ breast cancer, heart failure, asthma)
and 24 synthetic patients. Delete `backend/contextsync.db` to reset.

**Production build:** `npm run build` in `frontend/`. FastAPI then serves the built app from
http://127.0.0.1:8000 directly.

## Configuration (`backend/.env`, see `.env.example`)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Empty → SQLite. PostgreSQL: `postgresql+psycopg2://user:pass@host:5432/contextsync` (and `pip install psycopg2-binary`) |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Any OpenAI-compatible endpoint. Llama via Ollama: `http://localhost:11434/v1`, `llama3.1`. GPT: `https://api.openai.com/v1`, `gpt-4o-mini`. Empty → rule-based template explanations |
| `LLM_TOP_K` | How many top candidates per matching run get an LLM explanation (default 5) |
| `SECRET_KEY` | Signs auth tokens. Change it in production |

## How it works (mapped to the proposed methodology)

1. **Collect** – Trials are pasted or uploaded as PDF/TXT. Patients are entered manually or imported as FHIR bundles
   (Patient, Condition, MedicationStatement/Request, Observation, DocumentReference).
2. **Preprocess** – Unicode/operator normalisation, sentence splitting, section detection
   (`Inclusion Criteria:` / `Exclusion Criteria:`), and bullet and wrapped-line handling.
3. **Extract criteria (NLP)** – `app/nlp/criteria_extractor.py` turns each criterion into structured checks:
   age ranges, sex, diagnoses, medications (with class hierarchy, e.g. empagliflozin → SGLT2 inhibitor), and lab thresholds
   (`HbA1c between 7% and 10.5%`, `eGFR < 30`). Criteria that can't be structured become semantic-review checks.
4. **Patient features** – `app/nlp/concepts.py` recognises concepts in diagnosis lists *and* free-text notes, with
   NegEx-style negation ("denies pancreatitis", "never smoker", "family history of …").
5. **Match** – `app/services/matcher.py` evaluates every criterion as met / not met / unknown with evidence.
   A TF-IDF vector store (`app/services/vector_store.py`) supplies patient–trial semantic similarity and finds
   supporting sentences in clinical notes for free-text criteria.
6. **Explain** – `app/services/explainer.py` uses Llama/GPT, grounded only in the extracted evidence. Without an LLM it
   falls back to a deterministic template.
7. **Rank** – Confidence = 85% rule confidence (direct evidence 1.0, inferred absence 0.85, semantic 0.7,
   unknown 0.4) + 15% semantic similarity. Ineligible patients are down-weighted.
   Status is *Eligible*, *Needs review* (missing data) or *Not eligible*.
8. **Store & manage** – Results persist in `patient_trial_matches`. Coordinators approve, contact, enrol or reject
   candidates. Every action is written to an audit log.

## Project structure

```
backend/app/
  main.py            FastAPI app, startup seeding, static frontend
  models.py          Researcher, ClinicalTrial, EligibilityCriterion, Patient, PatientTrialMatch, AuditLog
  auth.py            PBKDF2 password hashing, signed bearer tokens
  nlp/               vocabulary, concept + negation detection, criteria extraction
  services/          matcher, vector store, LLM explainer, FHIR import/export, document parsing
  routers/           auth, dashboard, trials, patients, matches
frontend/src/
  pages/             Dashboard, Trials, TrialNew, TrialDetail, Patients, PatientDetail, PatientForm, Login
  components/        Layout, MatchDrawer (evidence + review), CriteriaList, ui
samples/             sample_protocol.txt, sample_fhir_bundle.json
```

## Demo script

1. Open **Clinical Trials → GLYCO-CONTROL** → *Run AI matching*. Rajesh Kumar is eligible, Priya Sharma needs review
   (eGFR missing), and the others are excluded for insulin use, pregnancy, pancreatitis, age, HbA1c or eGFR.
   Click a row to see per-criterion evidence and the explanation.
2. **New trial** → *Upload PDF/TXT* → `samples/sample_protocol.txt` → preview the extracted criteria → save → run matching.
3. **Patients** → *Import FHIR bundle* → `samples/sample_fhir_bundle.json` → open the patient → *Find matching trials*.

## Limitations / future work

- Temporal qualifiers ("within the past 6 months") and unit conversion are not yet evaluated.
- The vocabulary in `app/nlp/vocabulary.py` is curated. Production use would map to UMLS/SNOMED CT and could swap the
  TF-IDF store for transformer embeddings (e.g. BioBERT) in FAISS/ChromaDB behind the same interface.
- This is a decision-support tool. The principal investigator must confirm eligibility.
