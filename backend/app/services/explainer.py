"""Explainable eligibility decisions.

If an OpenAI-compatible LLM endpoint is configured (Llama via Ollama / vLLM,
or GPT via OpenAI) it writes a clinician-facing explanation grounded strictly
in the evidence produced by the matcher. Otherwise (or on failure) a
deterministic template explanation is used.
"""
import json
import logging

import httpx

from ..config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, llm_enabled

log = logging.getLogger(__name__)

STATUS_TEXT = {
    "eligible": "ELIGIBLE",
    "potentially_eligible": "POTENTIALLY ELIGIBLE (needs review)",
    "ineligible": "NOT ELIGIBLE",
}


def _first_evidence(r: dict) -> str:
    for chk in r["checks"]:
        if chk.get("evidence"):
            return chk["evidence"]
    return ""


def template_explanation(trial, patient, age, result: dict) -> str:
    results = result["criteria_results"]
    met = [r for r in results if r["status"] == "met"]
    unmet = [r for r in results if r["status"] == "not_met"]
    unknown = [r for r in results if r["status"] == "unknown"]
    who = f"{patient.name} ({age if age is not None else '?'} y, {patient.gender})"
    lines = [
        f"{who} is assessed as {STATUS_TEXT[result['eligibility_status']]} for “{trial.title}” "
        f"with a confidence score of {result['confidence_score']:.0f}%. "
        f"{len(met)} of {len(results)} criteria are satisfied.",
    ]
    if unmet:
        lines.append("\nBlocking criteria:")
        lines += [f"• [{r['type']}] {r['description']} — {_first_evidence(r)}" for r in unmet]
    key_inclusions = [r for r in met if r["type"] == "inclusion"][:4]
    if key_inclusions:
        lines.append("\nKey supporting evidence:")
        lines += [f"• {r['description']} — {_first_evidence(r)}" for r in key_inclusions]
    if unknown:
        lines.append("\nUnresolved criteria:")
        lines += [f"• [{r['type']}] {r['description']} — {_first_evidence(r)}" for r in unknown]
    if result["missing_tests"]:
        tests = ", ".join(t["test"] for t in result["missing_tests"])
        lines.append(f"\nRecommended next step: obtain {tests} to complete the eligibility assessment.")
    if result["eligibility_status"] == "eligible":
        lines.append("\nRecommendation: refer to the study team for investigator review and consent discussion.")
    elif result["eligibility_status"] == "potentially_eligible":
        lines.append("\nRecommendation: verify unresolved criteria before contacting the patient.")
    lines.append("\nFinal eligibility must be confirmed by the principal investigator.")
    return "\n".join(lines)


def _llm_payload(trial, patient, age, result: dict) -> dict:
    return {
        "trial": {"title": trial.title, "condition": trial.condition, "phase": trial.phase},
        "patient": {"name": patient.name, "age": age, "sex": patient.gender},
        "status": result["eligibility_status"],
        "confidence_score": result["confidence_score"],
        "criteria": [
            {"type": r["type"], "criterion": r["description"], "status": r["status"],
             "evidence": [c["evidence"] for c in r["checks"]]}
            for r in result["criteria_results"]
        ],
        "missing_tests": [t["test"] for t in result["missing_tests"]],
    }


SYSTEM_PROMPT = (
    "You are a clinical research assistant helping trial coordinators screen patients. "
    "Explain the eligibility decision using ONLY the evidence provided; never invent clinical facts. "
    "Write at most 170 words in plain text: one summary sentence with the status and confidence, then short "
    "bullet points ('• ') covering decisive criteria, unresolved items and missing tests to order, then a "
    "one-line recommendation. End by noting the principal investigator must confirm eligibility."
)


def llm_explanation(trial, patient, age, result: dict) -> str | None:
    if not llm_enabled():
        return None
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    body = {
        "model": LLM_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(_llm_payload(trial, patient, age, result), ensure_ascii=False)},
        ],
    }
    try:
        resp = httpx.post(f"{LLM_BASE_URL}/chat/completions", json=body, headers=headers, timeout=LLM_TIMEOUT)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text or None
    except Exception as exc:  # network errors, bad responses -> fall back to template
        log.warning("LLM explanation failed: %s", exc)
        return None


def explain(trial, patient, age, result: dict, use_llm: bool = False) -> tuple[str, str]:
    if use_llm:
        text = llm_explanation(trial, patient, age, result)
        if text:
            return text, "llm"
    return template_explanation(trial, patient, age, result), "template"
