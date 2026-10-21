"""Extract inclusion / exclusion criteria from free-text trial protocols and convert
each criterion into a structured, machine-evaluable rule.

A criterion's structured_rule looks like:
    {"checks": [ {"kind": "age", "min": 18, "max": 75, ...},
                 {"kind": "condition", "any_of": ["type 2 diabetes"]},
                 {"kind": "lab", "lab": "hba1c", "min": 7.0, "max": 10.5, ...},
                 {"kind": "text", "text": "..."} ],
     "logic": "all"}
"""
import re

from .concepts import find_mentions, normalize_text
from .vocabulary import lab_label, lab_unit

NUM = r"(\d+(?:\.\d+)?)"

_INCL_HDR = re.compile(r"^\s*(?:key\s+|main\s+)?inclusion(?:\s+criteria)?\s*[:\-]?\s*", re.I)
_EXCL_HDR = re.compile(r"^\s*(?:key\s+|main\s+)?exclusion(?:\s+criteria)?\s*[:\-]?\s*", re.I)
_OTHER_HDR = re.compile(r"^\s*(?:study\s+)?(?:objectives?|outcomes?|design|interventions?|background|summary|"
                        r"primary\s+endpoint|secondary\s+endpoints?|contacts?|locations?)\s*:?\s*$", re.I)
_BULLET = re.compile(r"^\s*(?:[-*+>]|\(?\d{1,2}[.)]|\(?[a-zA-Z][.)]|[ivx]{1,4}[.)])\s+")

_PREFIX_OPS = [
    (r">=|=>|at least|no less than|greater than or equal to|minimum(?: of)?|of at least", ">="),
    (r"<=|=<|at most|no more than|less than or equal to|up to|maximum(?: of)?|not exceeding", "<="),
    (r">|greater than|more than|above|over|older than|exceeding|higher than", ">"),
    (r"<|less than|below|under|younger than|lower than", "<"),
]
_SUFFIX_OPS = [
    (r"or older|or more|or greater|or above|and above|and older|or higher|\+", ">="),
    (r"or younger|or less|or below|and below|and younger|or lower|or under", "<="),
]
_UNIT = r"\s*(?:%|years?(?: of age| old)?|yrs?|kg/m2|kg/m\^?2|mg/dl|mmol/l|ml/min(?:/1\.73\s*m2)?|pg/ml|ng/ml|" \
        r"g/dl|u/l|iu/l|mmhg|cells/ul|cells/mm3|x\s*10\^?9/l|/ul|predicted)?"
_PREFIX_RE = re.compile(
    r"(?<![a-z0-9])(?:" + "|".join(f"(?P<p{i}>{pat})" for i, (pat, _) in enumerate(_PREFIX_OPS)) +
    r")\s*(?:a\s+|of\s+)?(?P<num>\d+(?:\.\d+)?)")
_SUFFIX_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)" + _UNIT + r"\s*(?:" +
    "|".join(f"(?P<s{i}>{pat})" for i, (pat, _) in enumerate(_SUFFIX_OPS)) + r")")


def _bounds(segment: str, max_value: float | None = None) -> dict | None:
    """Parse numeric bounds out of a short text segment."""
    s = segment.lower()
    m = re.search(r"between\s*" + NUM + _UNIT + r"\s*(?:and|-|to)\s*" + NUM, s) or \
        re.search(NUM + _UNIT + r"\s*(?:-|to)\s*" + NUM, s)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if lo <= hi and (max_value is None or hi <= max_value):
            return {"min": lo, "max": hi, "min_inclusive": True, "max_inclusive": True}
    found: list[tuple[int, str, float]] = []  # (position, op, value)
    for m in _PREFIX_RE.finditer(s):
        op = next(o for i, (_, o) in enumerate(_PREFIX_OPS) if m.group(f"p{i}"))
        found.append((m.start(), op, float(m.group("num"))))
    for m in _SUFFIX_RE.finditer(s):
        op = next(o for i, (_, o) in enumerate(_SUFFIX_OPS) if m.group(f"s{i}"))
        found.append((m.start(), op, float(m.group("num"))))
    result: dict = {}
    for _, op, value in sorted(found):
        if max_value is not None and value > max_value:
            continue
        if op in (">=", ">") and "min" not in result:
            result.update(min=value, min_inclusive=op == ">=")
        elif op in ("<=", "<") and "max" not in result:
            result.update(max=value, max_inclusive=op == "<=")
    return result or None


def bound_label(b: dict, unit: str = "") -> str:
    parts = []
    if "min" in b:
        parts.append(f"{'≥' if b.get('min_inclusive', True) else '>'} {b['min']:g}")
    if "max" in b:
        parts.append(f"{'≤' if b.get('max_inclusive', True) else '<'} {b['max']:g}")
    return " and ".join(parts) + (f" {unit}" if unit else "")


_AGE_CONTEXT = re.compile(r"\b(age[ds]?|aged|years? old|of age|older|younger|adults?|children)\b", re.I)


def _extract_age(text: str) -> dict | None:
    if not _AGE_CONTEXT.search(text):
        return None
    m = re.search(r"\bage[ds]?\b(?:\s+of)?(.{0,50})", text, re.I)
    candidates = [m.group(1)] if m else []
    for mm in re.finditer(r"\b\d{1,3}\s*(?:years?|yrs?)\b", text, re.I):
        candidates.append(text[max(0, mm.start() - 30):mm.end() + 25])
    m2 = re.search(r"\(\s*(?:>=|<=|>|<)\s*\d{1,3}\s*(?:years?|yrs?)?\s*\)", text)
    if m2:
        candidates.append(m2.group(0).strip("()"))
    merged: dict = {}
    for c in candidates:
        b = _bounds(c, max_value=120) or {}
        for side in ("min", "max"):
            if side in b and side not in merged:
                merged[side], merged[f"{side}_inclusive"] = b[side], b[f"{side}_inclusive"]
    if "min" not in merged and "max" not in merged:
        return None
    return {"kind": "age", **merged, "label": "Age " + bound_label(merged, "years")}


def _extract_gender(text: str) -> dict | None:
    t = text.lower()
    female = re.search(r"\b(female|females|women|woman|girls?|postmenopausal|premenopausal)\b", t)
    male = re.search(r"\b(male|males|men|man|boys?)\b", t)
    if re.search(r"\b(both sexes|either sex|any gender|all genders)\b", t) or (female and male):
        return None
    if female:
        return {"kind": "gender", "value": "female", "label": "Sex: female"}
    if male:
        return {"kind": "gender", "value": "male", "label": "Sex: male"}
    return None


_RELATIVE_LIMIT = re.compile(NUM + r"\s*(?:x|times)\s*(?:the\s*)?(?:uln|upper limit|lln|lower limit)", re.I)


def _extract_labs(text: str, mentions) -> list[dict]:
    labs = [m for m in mentions if m.kind == "lab"]
    checks = []
    for i, m in enumerate(labs):
        end = labs[i + 1].start if i + 1 < len(labs) else len(text)
        seg = text[m.end:min(end, m.end + 80)]
        # values relative to ULN can't be evaluated without reference ranges
        if _RELATIVE_LIMIT.search(seg):
            continue
        b = _bounds(seg)
        if not b:
            continue
        unit = lab_unit(m.canonical)
        checks.append({"kind": "lab", "lab": m.canonical, **b, "unit": unit,
                       "label": f"{lab_label(m.canonical)} {bound_label(b, unit)}"})
    return checks


def _concept_check(kind: str, mentions) -> dict | None:
    names = []
    for m in mentions:
        if m.kind == kind and m.canonical not in names:
            names.append(m.canonical)
    if not names:
        return None
    pretty = " or ".join(names)
    label = ("Diagnosis: " if kind == "condition" else "Medication: ") + pretty
    return {"kind": kind, "any_of": names, "label": label}


_CATEGORY = {"age": "demographic", "gender": "demographic", "condition": "diagnosis",
             "medication": "medication", "lab": "lab", "text": "other"}


def structure_criterion(text: str, ctype: str) -> dict:
    """Turn one criterion sentence into {category, structured_rule, required_evidence}."""
    clean = normalize_text(text)
    mentions = [m for m in find_mentions(clean, detect_negation=False)]
    checks: list[dict] = []

    labs = _extract_labs(clean, mentions)
    # remove lab segments before age parsing so lab numbers aren't read as ages
    age_text = clean
    for m in (x for x in mentions if x.kind == "lab"):
        age_text = age_text.replace(clean[m.start:m.end], " ")
    age = _extract_age(age_text)
    gender = _extract_gender(clean)
    cond = _concept_check("condition", mentions)
    med = _concept_check("medication", mentions)

    for c in (age, gender, cond, med):
        if c:
            checks.append(c)
    checks.extend(labs)

    # a lone sex qualifier ("women of childbearing potential not using contraception")
    # is not the whole criterion - keep the free text for semantic evaluation too.
    if not checks or all(c["kind"] == "gender" for c in checks):
        checks.append({"kind": "text", "text": clean, "label": "Requires review: " + clean[:80]})

    primary = next((c for c in checks if c["kind"] not in ("gender", "text")), checks[0])
    evidence = []
    for c in checks:
        if c["kind"] == "age":
            evidence.append("Date of birth")
        elif c["kind"] == "gender":
            evidence.append("Recorded sex")
        elif c["kind"] == "condition":
            evidence.append("Diagnoses / clinical notes")
        elif c["kind"] == "medication":
            evidence.append("Medication list / notes")
        elif c["kind"] == "lab":
            evidence.append(f"Lab: {lab_label(c['lab'])}")
        else:
            evidence.append("Clinical notes (semantic match)")
    return {
        "type": ctype,
        "category": _CATEGORY[primary["kind"]],
        "description": text.strip(),
        "structured_rule": {"checks": checks, "logic": "all"},
        "required_evidence": "; ".join(dict.fromkeys(evidence)),
    }


def _split_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        is_bullet = bool(_BULLET.match(line))
        stripped = _BULLET.sub("", line).strip()
        if not stripped:
            continue
        # continuation of a wrapped line
        if items and not is_bullet and (stripped[0].islower() or items[-1].endswith((",", "-", "and", "or"))):
            items[-1] = f"{items[-1]} {stripped}"
            continue
        items.append(stripped)
    out = []
    for item in items:
        # long paragraphs -> sentences
        parts = re.split(r"(?<=[.;])\s+(?=[A-Z])", item) if len(item) > 160 else [item]
        out.extend(p.strip().rstrip(".;").strip() for p in parts if len(p.strip()) > 2)
    return out


def split_sections(protocol_text: str) -> tuple[list[str], list[str]]:
    text = normalize_text(protocol_text or "")
    inclusion, exclusion = [], []
    current = None
    found_header = False
    for line in text.splitlines():
        if _INCL_HDR.match(line) and re.search(r"inclusion", line, re.I) and len(line) < 200:
            current, found_header = inclusion, True
            rest = _INCL_HDR.sub("", line, count=1)
            if rest.strip():
                current.append(rest)
            continue
        if _EXCL_HDR.match(line) and len(line) < 200:
            current, found_header = exclusion, True
            rest = _EXCL_HDR.sub("", line, count=1)
            if rest.strip():
                current.append(rest)
            continue
        if _OTHER_HDR.match(line):
            current = None
            continue
        if current is not None:
            current.append(line)
    if not found_header:
        # no section headers: treat every line as an inclusion criterion
        inclusion = text.splitlines()
    return _split_items(inclusion), _split_items(exclusion)


def extract_criteria(protocol_text: str) -> list[dict]:
    inclusion, exclusion = split_sections(protocol_text)
    criteria = [structure_criterion(t, "inclusion") for t in inclusion]
    criteria += [structure_criterion(t, "exclusion") for t in exclusion]
    for i, c in enumerate(criteria):
        c["position"] = i
    return criteria
