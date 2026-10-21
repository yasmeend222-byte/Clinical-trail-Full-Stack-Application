"""Synthetic demo data (no real patient information)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import ClinicalTrial, EligibilityCriterion, Patient, Researcher
from .nlp.criteria_extractor import extract_criteria

DEMO_EMAIL = "admin@contextsync.dev"
DEMO_PASSWORD = "admin123"

TRIALS = [
    {
        "trial_code": "CS-DM-301", "phase": "Phase III", "condition": "Type 2 Diabetes", "sponsor": "Demo Pharma",
        "title": "GLYCO-CONTROL: Once-weekly GLP-1 receptor agonist in adults with uncontrolled type 2 diabetes",
        "description": "Randomized, double-blind, placebo-controlled study evaluating glycaemic control with a "
                       "once-weekly GLP-1 receptor agonist added to metformin.",
        "protocol_text": """Inclusion Criteria:
1. Male or female aged 18 to 75 years
2. Diagnosis of type 2 diabetes mellitus for at least 6 months
3. HbA1c between 7.0% and 10.5% at screening
4. Currently taking metformin at a stable dose for at least 3 months
5. Body mass index (BMI) between 25 and 45 kg/m2

Exclusion Criteria:
1. Type 1 diabetes mellitus
2. Estimated glomerular filtration rate (eGFR) < 30 mL/min/1.73m2
3. History of pancreatitis
4. Women who are pregnant, breastfeeding, or planning pregnancy
5. Current treatment with insulin
6. Myocardial infarction or stroke within the past 6 months
""",
    },
    {
        "trial_code": "CS-ONC-204", "phase": "Phase II", "condition": "HER2-positive Breast Cancer",
        "sponsor": "Demo Oncology Group",
        "title": "HER2-TARGET: Novel antibody-drug conjugate in HER2-positive early breast cancer",
        "description": "Open-label study of a HER2-directed antibody-drug conjugate in treatment-naive "
                       "HER2-positive breast cancer.",
        "protocol_text": """Inclusion Criteria:
- Female patients aged 18 years or older
- Histologically confirmed HER2-positive breast cancer (stage I-III)
- ECOG performance status 0-1
- Left ventricular ejection fraction (LVEF) >= 50%
- Absolute neutrophil count >= 1.5 x 10^9/L
- Platelet count >= 100 x 10^9/L

Exclusion Criteria:
- Prior treatment with trastuzumab or other anti-HER2 therapy
- Known active brain metastases
- Pregnancy or lactation
- Known HIV infection
- Symptomatic congestive heart failure (NYHA class II-IV)
""",
    },
    {
        "trial_code": "CS-CV-310", "phase": "Phase III", "condition": "Heart Failure",
        "sponsor": "Demo Cardio Research",
        "title": "HEART-RESTORE: SGLT2 inhibitor in heart failure with reduced ejection fraction",
        "description": "Event-driven trial assessing cardiovascular death and heart-failure hospitalisation.",
        "protocol_text": """Inclusion Criteria:
- Men and women aged 40 to 85 years
- Diagnosis of chronic heart failure (NYHA class II-IV) for at least 3 months
- LVEF <= 40% documented by echocardiography within 12 months
- NT-proBNP >= 600 pg/mL

Exclusion Criteria:
- Current treatment with an SGLT2 inhibitor
- eGFR < 25 mL/min/1.73m2
- Type 1 diabetes
- Systolic blood pressure < 95 mmHg
- History of heart transplant
""",
    },
    {
        "trial_code": "CS-RESP-202", "phase": "Phase II", "condition": "Severe Eosinophilic Asthma",
        "sponsor": "Demo Respiratory",
        "title": "BREATHE-WELL: Anti-IL-5 biologic for severe eosinophilic asthma",
        "description": "Evaluates annualised exacerbation rate with add-on biologic therapy.",
        "protocol_text": """Inclusion Criteria:
- Male or female patients aged 12 to 65 years
- Physician-diagnosed asthma for at least 12 months
- Blood eosinophil count >= 300 cells/uL at screening
- Pre-bronchodilator FEV1 between 40% and 80% of predicted
- Treatment with medium- or high-dose inhaled corticosteroids for at least 12 months

Exclusion Criteria:
- Current smoker
- Diagnosis of COPD or other significant lung disease
- Pregnant or breastfeeding
- Known parasitic infection within 6 months
""",
    },
]

D = "2026-08-20"


def _labs(**kw):
    names = {"hba1c": ("HbA1c", "%"), "bmi": ("BMI", "kg/m2"), "egfr": ("eGFR", "mL/min/1.73m2"),
             "lvef": ("LVEF", "%"), "ntprobnp": ("NT-proBNP", "pg/mL"), "sbp": ("Systolic blood pressure", "mmHg"),
             "eos": ("Blood eosinophil count", "cells/uL"), "fev1": ("FEV1 % predicted", "%"),
             "ecog": ("ECOG performance status", ""), "anc": ("Absolute neutrophil count", "x10^9/L"),
             "plt": ("Platelet count", "x10^9/L"), "ldl": ("LDL cholesterol", "mg/dL"),
             "tsh": ("TSH", "mIU/L")}
    return [{"name": names[k][0], "value": v, "unit": names[k][1], "date": D} for k, v in kw.items()]


PATIENTS = [
    # ---- diabetes cohort ----
    ("MRN-1001", "Rajesh Kumar", date(1968, 4, 12), "male", "Hyderabad",
     ["Type 2 diabetes mellitus", "Essential hypertension"], ["Metformin 1000 mg BID", "Lisinopril 10 mg"],
     _labs(hba1c=8.4, bmi=31.2, egfr=78, ldl=112),
     "Type 2 diabetes diagnosed in 2015. Hypertension since 2018.",
     "Suboptimal glycaemic control despite adherence to metformin. Denies history of pancreatitis. "
     "No chest pain or neuropathic symptoms. Interested in research participation."),
    ("MRN-1002", "Priya Sharma", date(1975, 9, 3), "female", "Bengaluru",
     ["Type 2 diabetes mellitus"], ["Metformin 850 mg BID"], _labs(hba1c=7.6, bmi=28.5),
     "T2DM diagnosed 2019.", "Not pregnant, post-menopausal. Kidney function test pending. Diet counselling given."),
    ("MRN-1003", "Anil Verma", date(1960, 1, 22), "male", "Delhi",
     ["Type 2 diabetes mellitus", "Hyperlipidemia"], ["Metformin 1000 mg BID", "Insulin glargine 20 units nightly",
                                                      "Atorvastatin 40 mg"],
     _labs(hba1c=9.1, bmi=33.0, egfr=65), "Diabetes for 12 years.", "Started basal insulin in 2024."),
    ("MRN-1004", "Lakshmi Reddy", date(1958, 7, 30), "female", "Vijayawada",
     ["Type 2 diabetes mellitus", "Chronic kidney disease stage 4"], ["Metformin 500 mg daily", "Amlodipine 5 mg"],
     _labs(hba1c=8.0, bmi=29.4, egfr=24), "", "Nephrology follow-up for progressive CKD."),
    ("MRN-1005", "Mohammed Ali", date(1950, 3, 10), "male", "Chennai",
     ["Type 2 diabetes mellitus"], ["Metformin 1000 mg BID"], _labs(hba1c=7.9, bmi=27.1, egfr=55),
     "", "Elderly patient, independent in daily activities."),
    ("MRN-1006", "Sneha Patel", date(1990, 11, 18), "female", "Ahmedabad",
     ["Type 2 diabetes mellitus"], ["Metformin 500 mg BID"], _labs(hba1c=7.2, bmi=26.3, egfr=98),
     "", "Currently 14 weeks pregnant; obstetric care co-managed."),
    ("MRN-1007", "Vikram Singh", date(1972, 6, 5), "male", "Jaipur",
     ["Type 2 diabetes mellitus"], ["Metformin 1000 mg BID"], _labs(hba1c=8.8, bmi=30.4, egfr=80),
     "History of acute pancreatitis (2021) related to alcohol.", "Abstinent since 2021."),
    ("MRN-1008", "Deepa Nair", date(1966, 2, 14), "female", "Kochi",
     ["Type 2 diabetes mellitus", "Obesity"], ["Metformin 1000 mg BID", "Glimepiride 2 mg"],
     _labs(hba1c=11.2, bmi=34.8, egfr=72), "", "Poorly controlled diabetes, frequent hyperglycaemia."),
    ("MRN-1009", "Arjun Mehta", date(1980, 8, 25), "male", "Mumbai",
     ["Prediabetes"], ["Metformin 500 mg daily"], _labs(hba1c=6.1, bmi=29.0, egfr=95),
     "", "Lifestyle modification advised. No diabetes."),
    ("MRN-1010", "Kavya Iyer", date(1985, 12, 1), "female", "Chennai",
     ["Type 1 diabetes mellitus"], ["Insulin lispro", "Insulin glargine"], _labs(hba1c=7.8, bmi=23.1, egfr=101),
     "Type 1 diabetes since childhood.", "Uses carbohydrate counting."),
    # ---- oncology cohort ----
    ("MRN-2001", "Meera Joshi", date(1972, 5, 9), "female", "Pune",
     ["HER2-positive breast cancer, stage IIA"], [],
     _labs(ecog=1, lvef=60, anc=3.2, plt=240),
     "Diagnosed by core biopsy in July 2026, treatment naive.",
     "MRI brain: no evidence of brain metastases. HIV negative. Not pregnant."),
    ("MRN-2002", "Anjali Gupta", date(1965, 10, 21), "female", "Lucknow",
     ["HER2-positive breast cancer, stage III"], ["Letrozole 2.5 mg"],
     _labs(ecog=1, lvef=55, anc=2.8, plt=210),
     "Received trastuzumab and pertuzumab with docetaxel in 2023-2024.", "Now with local recurrence."),
    ("MRN-2003", "Fatima Shaikh", date(1979, 3, 27), "female", "Hyderabad",
     ["HER2-positive breast cancer, stage I"], [], _labs(ecog=0, anc=2.1, plt=180),
     "", "Echocardiogram not yet performed. No cardiac symptoms."),
    ("MRN-2004", "Sunita Rao", date(1969, 9, 14), "female", "Visakhapatnam",
     ["Triple-negative breast cancer, stage II"], [], _labs(ecog=1, lvef=62, anc=2.5, plt=260),
     "", "HER2 negative on IHC."),
    ("MRN-2005", "Rekha Menon", date(1961, 1, 5), "female", "Thiruvananthapuram",
     ["HER2-positive breast cancer, stage IV", "Brain metastases"], ["Dexamethasone 4 mg"],
     _labs(ecog=2, lvef=58, anc=2.0, plt=150), "", "Multiple active brain lesions on MRI."),
    # ---- cardiology cohort ----
    ("MRN-3001", "Suresh Babu", date(1955, 2, 18), "male", "Guntur",
     ["Heart failure with reduced ejection fraction", "Hypertension"],
     ["Carvedilol 12.5 mg BID", "Sacubitril/valsartan 49/51 mg BID", "Furosemide 40 mg"],
     _labs(lvef=32, ntprobnp=1450, egfr=58, sbp=118),
     "Ischaemic cardiomyopathy diagnosed 2022.", "NYHA class II symptoms. No history of heart transplant."),
    ("MRN-3002", "Ramesh Iyer", date(1949, 8, 8), "male", "Madurai",
     ["Heart failure with reduced ejection fraction", "Type 2 diabetes mellitus"],
     ["Empagliflozin 10 mg", "Metoprolol 50 mg", "Metformin 500 mg BID"],
     _labs(lvef=30, ntprobnp=2100, egfr=48, sbp=112, hba1c=7.4, bmi=27.5), "", "Stable on guideline therapy."),
    ("MRN-3003", "Geeta Kapoor", date(1952, 12, 30), "female", "Chandigarh",
     ["Congestive heart failure"], ["Bisoprolol 5 mg", "Spironolactone 25 mg"],
     _labs(lvef=35, egfr=45, sbp=110), "", "NT-proBNP to be repeated at next visit."),
    ("MRN-3004", "Joseph Thomas", date(1962, 4, 4), "male", "Kottayam",
     ["Coronary artery disease", "Hyperlipidemia"], ["Aspirin 75 mg", "Rosuvastatin 20 mg"],
     _labs(lvef=55, egfr=82, sbp=128, ldl=68), "Myocardial infarction in March 2024, PCI to LAD.",
     "No heart failure symptoms."),
    # ---- respiratory cohort ----
    ("MRN-4001", "Aisha Khan", date(1998, 6, 16), "female", "Hyderabad",
     ["Severe eosinophilic asthma"], ["Fluticasone/salmeterol 500/50 BID", "Montelukast 10 mg"],
     _labs(eos=450, fev1=62), "Asthma since age 9.", "Never smoker. Three exacerbations requiring steroids in the last year."),
    ("MRN-4002", "Rohit Das", date(1988, 1, 11), "male", "Kolkata",
     ["Asthma"], ["Budesonide/formoterol 200/6"], _labs(eos=380, fev1=70),
     "", "Current smoker, about 10 cigarettes per day."),
    ("MRN-4003", "Nisha Verghese", date(2001, 9, 9), "female", "Kochi",
     ["Asthma"], ["Budesonide 400 mcg BID"], _labs(fev1=68), "Asthma diagnosed 2015.",
     "Blood eosinophil count not measured recently. Non-smoker."),
    ("MRN-4004", "Harish Pillai", date(1957, 11, 23), "male", "Kozhikode",
     ["COPD"], ["Tiotropium 18 mcg", "Fluticasone 250 mcg"], _labs(eos=150, fev1=48),
     "Former smoker, 30 pack-years, quit 2019.", ""),
    # ---- other ----
    ("MRN-5001", "Neha Agarwal", date(1993, 7, 2), "female", "Indore",
     ["Hypothyroidism"], ["Levothyroxine 50 mcg"], _labs(tsh=2.4, bmi=22.0), "", "Routine follow-up."),
]


def seed(db: Session) -> None:
    if db.scalar(select(Researcher).limit(1)):
        return
    admin = Researcher(name="Dr. K. Keerthana", email=DEMO_EMAIL, role="Principal Investigator",
                       password_hash=hash_password(DEMO_PASSWORD))
    db.add(admin)
    db.flush()
    for t in TRIALS:
        trial = ClinicalTrial(**t, researcher_id=admin.id)
        for c in extract_criteria(t["protocol_text"]):
            trial.criteria.append(EligibilityCriterion(**c))
        db.add(trial)
    for mrn, name, dob, gender, city, dx, meds, labs, history, notes in PATIENTS:
        db.add(Patient(mrn=mrn, name=name, birth_date=dob, gender=gender,
                       demographics={"city": city, "country": "India"}, diagnoses=dx, medications=meds,
                       lab_results=labs, medical_history=history, clinical_notes=notes, source="seed"))
    db.commit()
