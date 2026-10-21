"""Curated medical vocabulary used by the NLP layer.

Each concept has a canonical name, synonyms and optional parent concepts
(e.g. "empagliflozin" -> "sglt2 inhibitor"), so that a criterion written at
class level ("SGLT2 inhibitor", "malignancy") matches specific patient facts.
Extend these tables to support more therapeutic areas.
"""

# canonical: (synonyms, parents)
CONDITIONS: dict[str, tuple[list[str], list[str]]] = {
    "diabetes": (["diabetes", "diabetes mellitus", "diabetic"], []),
    "type 2 diabetes": (["type 2 diabetes", "type ii diabetes", "t2dm", "t2d", "diabetes mellitus type 2",
                         "type 2 diabetes mellitus", "non-insulin dependent diabetes", "niddm"], ["diabetes"]),
    "type 1 diabetes": (["type 1 diabetes", "type i diabetes", "t1dm", "t1d", "diabetes mellitus type 1",
                         "type 1 diabetes mellitus", "insulin-dependent diabetes", "iddm"], ["diabetes"]),
    "prediabetes": (["prediabetes", "pre-diabetes", "impaired glucose tolerance", "impaired fasting glucose"], []),
    "hypertension": (["hypertension", "htn", "high blood pressure"], []),
    "hyperlipidemia": (["hyperlipidemia", "dyslipidemia", "hypercholesterolemia", "high cholesterol"], []),
    "obesity": (["obesity", "obese", "morbid obesity"], []),
    "heart failure": (["heart failure", "chf", "congestive heart failure", "cardiac failure", "hfref", "hfpef",
                       "heart failure with reduced ejection fraction",
                       "heart failure with preserved ejection fraction"], ["cardiovascular disease"]),
    "coronary artery disease": (["coronary artery disease", "cad", "ischemic heart disease",
                                 "ischaemic heart disease"], ["cardiovascular disease"]),
    "myocardial infarction": (["myocardial infarction", "heart attack", "stemi", "nstemi", "mi"],
                              ["cardiovascular disease"]),
    "stroke": (["stroke", "cerebrovascular accident", "cva", "transient ischemic attack", "tia"],
               ["cardiovascular disease"]),
    "atrial fibrillation": (["atrial fibrillation", "afib", "a-fib"], ["cardiovascular disease"]),
    "cardiovascular disease": (["cardiovascular disease", "cardiac disease", "heart disease"], []),
    "heart transplant": (["heart transplant", "cardiac transplant", "heart transplantation"], ["organ transplant"]),
    "organ transplant": (["organ transplant", "solid organ transplant", "transplant recipient"], []),
    "chronic kidney disease": (["chronic kidney disease", "ckd", "renal insufficiency", "chronic renal failure",
                                "kidney disease", "end-stage renal disease", "esrd", "renal impairment"], []),
    "dialysis": (["dialysis", "hemodialysis", "haemodialysis", "peritoneal dialysis"], ["chronic kidney disease"]),
    "liver disease": (["liver disease", "hepatic impairment", "hepatic disease", "hepatic failure", "liver failure"], []),
    "cirrhosis": (["cirrhosis", "liver cirrhosis"], ["liver disease"]),
    "hepatitis b": (["hepatitis b", "hbv", "chronic hepatitis b"], ["liver disease"]),
    "hepatitis c": (["hepatitis c", "hcv", "chronic hepatitis c"], ["liver disease"]),
    "pancreatitis": (["pancreatitis", "acute pancreatitis", "chronic pancreatitis"], []),
    "hiv": (["hiv", "human immunodeficiency virus", "hiv infection", "aids"], []),
    "tuberculosis": (["tuberculosis", "tb"], []),
    "covid-19": (["covid-19", "covid", "sars-cov-2"], []),
    "malignancy": (["malignancy", "malignancies", "cancer", "carcinoma", "malignant neoplasm", "neoplasm"], []),
    "breast cancer": (["breast cancer", "breast carcinoma", "carcinoma of the breast", "invasive ductal carcinoma"],
                      ["malignancy"]),
    "her2-positive breast cancer": (["her2-positive breast cancer", "her2 positive breast cancer",
                                     "her2+ breast cancer", "her2-overexpressing breast cancer"], ["breast cancer"]),
    "her2-negative breast cancer": (["her2-negative breast cancer", "her2 negative breast cancer",
                                     "her2- breast cancer", "triple negative breast cancer",
                                     "triple-negative breast cancer"], ["breast cancer"]),
    "lung cancer": (["lung cancer", "nsclc", "non-small cell lung cancer", "small cell lung cancer",
                     "lung carcinoma", "lung adenocarcinoma"], ["malignancy"]),
    "prostate cancer": (["prostate cancer", "prostate carcinoma", "prostate adenocarcinoma"], ["malignancy"]),
    "colorectal cancer": (["colorectal cancer", "colon cancer", "rectal cancer"], ["malignancy"]),
    "brain metastases": (["brain metastases", "brain metastasis", "cns metastases", "brain mets"], ["malignancy"]),
    "asthma": (["asthma", "bronchial asthma", "eosinophilic asthma", "severe asthma"], []),
    "copd": (["copd", "chronic obstructive pulmonary disease", "emphysema", "chronic bronchitis"], []),
    "smoking": (["current smoker", "smoker", "smokes", "tobacco use", "cigarette smoking", "active smoker"], []),
    "parasitic infection": (["parasitic infection", "helminth infection", "helminthic infection",
                             "parasitic infestation"], []),
    "depression": (["depression", "major depressive disorder", "mdd", "depressive disorder"], []),
    "dementia": (["dementia"], []),
    "alzheimer's disease": (["alzheimer's disease", "alzheimers disease", "alzheimer disease", "alzheimer's"],
                            ["dementia"]),
    "parkinson's disease": (["parkinson's disease", "parkinsons disease", "parkinson disease"], []),
    "epilepsy": (["epilepsy", "seizure disorder", "seizures"], []),
    "multiple sclerosis": (["multiple sclerosis"], []),
    "rheumatoid arthritis": (["rheumatoid arthritis"], ["autoimmune disease"]),
    "psoriasis": (["psoriasis", "plaque psoriasis"], ["autoimmune disease"]),
    "lupus": (["lupus", "systemic lupus erythematosus", "sle"], ["autoimmune disease"]),
    "autoimmune disease": (["autoimmune disease", "autoimmune disorder"], []),
    "osteoarthritis": (["osteoarthritis"], []),
    "anemia": (["anemia", "anaemia"], []),
    "hypothyroidism": (["hypothyroidism"], []),
    "diabetic retinopathy": (["diabetic retinopathy", "proliferative retinopathy"], []),
    "pregnancy": (["pregnant", "pregnancy", "breastfeeding", "breast-feeding", "lactating", "lactation", "nursing"], []),
    "substance abuse": (["substance abuse", "drug abuse", "alcohol abuse", "alcoholism", "substance use disorder",
                         "alcohol use disorder"], []),
}

MEDICATIONS: dict[str, tuple[list[str], list[str]]] = {
    "metformin": (["metformin", "glucophage"], ["antidiabetic"]),
    "insulin": (["insulin", "insulin glargine", "insulin lispro", "insulin aspart", "basal insulin", "lantus"],
                ["antidiabetic"]),
    "sglt2 inhibitor": (["sglt2 inhibitor", "sglt2 inhibitors", "sglt-2 inhibitor", "sglt2i"], ["antidiabetic"]),
    "empagliflozin": (["empagliflozin", "jardiance"], ["sglt2 inhibitor"]),
    "dapagliflozin": (["dapagliflozin", "farxiga"], ["sglt2 inhibitor"]),
    "canagliflozin": (["canagliflozin"], ["sglt2 inhibitor"]),
    "glp-1 receptor agonist": (["glp-1 receptor agonist", "glp-1 agonist", "glp-1 ra", "glp-1"], ["antidiabetic"]),
    "semaglutide": (["semaglutide", "ozempic", "wegovy"], ["glp-1 receptor agonist"]),
    "liraglutide": (["liraglutide", "victoza"], ["glp-1 receptor agonist"]),
    "dulaglutide": (["dulaglutide", "trulicity"], ["glp-1 receptor agonist"]),
    "sulfonylurea": (["sulfonylurea", "sulfonylureas"], ["antidiabetic"]),
    "glipizide": (["glipizide"], ["sulfonylurea"]),
    "glimepiride": (["glimepiride"], ["sulfonylurea"]),
    "dpp-4 inhibitor": (["dpp-4 inhibitor", "sitagliptin", "linagliptin"], ["antidiabetic"]),
    "antidiabetic": (["antidiabetic", "oral hypoglycemic", "glucose-lowering therapy"], []),
    "statin": (["statin", "statins", "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin"], []),
    "ace inhibitor": (["ace inhibitor", "lisinopril", "enalapril", "ramipril"], ["antihypertensive"]),
    "arb": (["angiotensin receptor blocker", "losartan", "valsartan", "candesartan", "irbesartan"],
            ["antihypertensive"]),
    "sacubitril/valsartan": (["sacubitril/valsartan", "sacubitril", "entresto"], ["antihypertensive"]),
    "beta blocker": (["beta blocker", "beta-blocker", "metoprolol", "carvedilol", "bisoprolol", "atenolol"],
                     ["antihypertensive"]),
    "diuretic": (["diuretic", "furosemide", "hydrochlorothiazide", "spironolactone", "torsemide"],
                 ["antihypertensive"]),
    "calcium channel blocker": (["calcium channel blocker", "amlodipine", "diltiazem", "nifedipine"],
                                ["antihypertensive"]),
    "antihypertensive": (["antihypertensive", "antihypertensives"], []),
    "anticoagulant": (["anticoagulant", "anticoagulants", "anticoagulation", "warfarin", "apixaban",
                       "rivaroxaban", "dabigatran", "heparin", "enoxaparin"], []),
    "antiplatelet": (["antiplatelet", "aspirin", "clopidogrel", "ticagrelor"], []),
    "corticosteroid": (["corticosteroid", "corticosteroids", "systemic corticosteroids", "systemic steroids",
                        "steroids", "prednisone", "prednisolone", "dexamethasone", "methylprednisolone",
                        "hydrocortisone"], []),
    "inhaled corticosteroid": (["inhaled corticosteroid", "inhaled corticosteroids", "ics", "fluticasone",
                                "budesonide", "beclomethasone", "mometasone"], ["corticosteroid"]),
    "laba": (["long-acting beta agonist", "laba", "salmeterol", "formoterol", "vilanterol"], []),
    "bronchodilator": (["salbutamol", "albuterol", "bronchodilator"], []),
    "biologic therapy": (["biologic therapy", "biologics", "monoclonal antibody", "mepolizumab", "benralizumab",
                          "omalizumab", "dupilumab"], []),
    "chemotherapy": (["chemotherapy", "cisplatin", "carboplatin", "paclitaxel", "docetaxel", "doxorubicin",
                      "cyclophosphamide", "capecitabine"], []),
    "trastuzumab": (["trastuzumab", "herceptin"], ["anti-her2 therapy"]),
    "pertuzumab": (["pertuzumab", "perjeta"], ["anti-her2 therapy"]),
    "anti-her2 therapy": (["anti-her2 therapy", "her2-targeted therapy"], []),
    "immunotherapy": (["immunotherapy", "checkpoint inhibitor", "pembrolizumab", "nivolumab", "atezolizumab"], []),
    "hormone therapy": (["tamoxifen", "letrozole", "anastrozole", "aromatase inhibitor", "hormone therapy"], []),
    "immunosuppressant": (["immunosuppressant", "immunosuppressive therapy", "tacrolimus", "cyclosporine",
                           "mycophenolate", "methotrexate", "azathioprine"], []),
    "levothyroxine": (["levothyroxine", "synthroid"], []),
    "ssri": (["ssri", "sertraline", "fluoxetine", "escitalopram", "citalopram", "paroxetine"], []),
    "donepezil": (["donepezil"], []),
    "levodopa": (["levodopa", "carbidopa/levodopa"], []),
    "nsaid": (["nsaid", "nsaids", "ibuprofen", "naproxen", "diclofenac"], []),
    "investigational drug": (["investigational drug", "investigational product", "investigational agent",
                              "another clinical trial", "other clinical trial"], []),
}

# key: (display label, synonyms, default unit)
LABS: dict[str, tuple[str, list[str], str]] = {
    "hba1c": ("HbA1c", ["hba1c", "hb a1c", "hemoglobin a1c", "haemoglobin a1c", "glycated hemoglobin",
                        "glycated haemoglobin", "glycosylated hemoglobin", "a1c"], "%"),
    "fasting_glucose": ("Fasting plasma glucose", ["fasting plasma glucose", "fasting blood glucose",
                                                   "fasting glucose", "fpg"], "mg/dL"),
    "egfr": ("eGFR", ["egfr", "estimated glomerular filtration rate", "glomerular filtration rate", "gfr"],
             "mL/min/1.73m2"),
    "creatinine": ("Serum creatinine", ["serum creatinine", "creatinine"], "mg/dL"),
    "alt": ("ALT", ["alt", "alanine aminotransferase", "sgpt"], "U/L"),
    "ast": ("AST", ["ast", "aspartate aminotransferase", "sgot"], "U/L"),
    "bilirubin": ("Total bilirubin", ["total bilirubin", "bilirubin"], "mg/dL"),
    "hemoglobin": ("Hemoglobin", ["hemoglobin", "haemoglobin", "hgb", "hb"], "g/dL"),
    "platelets": ("Platelet count", ["platelet count", "platelets", "plt"], "x10^9/L"),
    "wbc": ("WBC", ["white blood cell count", "white blood cells", "wbc"], "x10^9/L"),
    "anc": ("Absolute neutrophil count", ["absolute neutrophil count", "neutrophil count", "anc"], "x10^9/L"),
    "eosinophils": ("Blood eosinophil count", ["blood eosinophil count", "eosinophil count", "eosinophils",
                                               "eos"], "cells/uL"),
    "bmi": ("BMI", ["bmi", "body mass index"], "kg/m2"),
    "systolic_bp": ("Systolic blood pressure", ["systolic blood pressure", "systolic bp", "sbp"], "mmHg"),
    "diastolic_bp": ("Diastolic blood pressure", ["diastolic blood pressure", "diastolic bp", "dbp"], "mmHg"),
    "ldl": ("LDL cholesterol", ["ldl cholesterol", "ldl-c", "ldl"], "mg/dL"),
    "total_cholesterol": ("Total cholesterol", ["total cholesterol"], "mg/dL"),
    "triglycerides": ("Triglycerides", ["triglycerides", "tg"], "mg/dL"),
    "potassium": ("Potassium", ["serum potassium", "potassium"], "mmol/L"),
    "sodium": ("Sodium", ["serum sodium", "sodium"], "mmol/L"),
    "tsh": ("TSH", ["tsh", "thyroid stimulating hormone"], "mIU/L"),
    "lvef": ("LVEF", ["left ventricular ejection fraction", "lvef", "ejection fraction"], "%"),
    "ntprobnp": ("NT-proBNP", ["nt-probnp", "nt probnp", "n-terminal pro-b-type natriuretic peptide"], "pg/mL"),
    "fev1": ("FEV1 (% predicted)", ["fev1", "forced expiratory volume"], "% predicted"),
    "ecog": ("ECOG performance status", ["ecog performance status", "ecog ps", "ecog"], ""),
    "psa": ("PSA", ["psa", "prostate-specific antigen", "prostate specific antigen"], "ng/mL"),
    "mmse": ("MMSE score", ["mmse", "mini-mental state examination"], ""),
}


def _expand_parents(vocab: dict[str, tuple[list[str], list[str]]], canonical: str) -> set[str]:
    out, stack = set(), [canonical]
    while stack:
        c = stack.pop()
        if c in out:
            continue
        out.add(c)
        if c in vocab:
            stack.extend(vocab[c][1])
    return out


def expand_condition(canonical: str) -> set[str]:
    return _expand_parents(CONDITIONS, canonical)


def expand_medication(canonical: str) -> set[str]:
    return _expand_parents(MEDICATIONS, canonical)


def lab_label(key: str) -> str:
    return LABS[key][0] if key in LABS else key


def lab_unit(key: str) -> str:
    return LABS[key][2] if key in LABS else ""
