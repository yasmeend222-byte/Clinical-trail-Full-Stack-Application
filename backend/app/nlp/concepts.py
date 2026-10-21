"""Dictionary-based medical concept recognition with NegEx-style negation detection."""
import re
from dataclasses import dataclass

from .vocabulary import CONDITIONS, LABS, MEDICATIONS

_UNICODE_MAP = {
    "≥": ">=", "≤": "<=", "–": "-", "—": "-", "−": "-", "µ": "u", "μ": "u", "×": "x",
    "’": "'", "‘": "'", "“": '"', "”": '"', "•": "-", " ": " ",
}


def normalize_text(text: str) -> str:
    for k, v in _UNICODE_MAP.items():
        text = text.replace(k, v)
    return text


@dataclass
class Mention:
    canonical: str
    kind: str  # condition | medication | lab
    start: int
    end: int
    text: str
    negated: bool = False
    sentence: str = ""


def _compile(vocab_items: list[tuple[str, str]]) -> tuple[re.Pattern, dict[str, str]]:
    """vocab_items: (synonym, canonical). Longest synonyms first so alternation prefers them."""
    lookup = {syn.lower(): canon for syn, canon in vocab_items}
    alts = sorted(lookup, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w-])(" + "|".join(re.escape(a) for a in alts) + r")(?![\w-])", re.I)
    return pattern, lookup


_COND_RE, _COND_LOOKUP = _compile([(s, c) for c, (syns, _) in CONDITIONS.items() for s in syns + [c]])
_MED_RE, _MED_LOOKUP = _compile([(s, c) for c, (syns, _) in MEDICATIONS.items() for s in syns + [c]])
_LAB_RE, _LAB_LOOKUP = _compile([(s, k) for k, (_, syns, _) in LABS.items() for s in syns])

_KINDS = [("condition", _COND_RE, _COND_LOOKUP), ("medication", _MED_RE, _MED_LOOKUP), ("lab", _LAB_RE, _LAB_LOOKUP)]

_NEG_PRE = re.compile(
    r"\b(no|not|denies|denied|deny|without|negative for|free of|ruled out|rule out|r/o|absence of|never|"
    r"family history of|fhx|mother|father|sister|brother|grandmother|grandfather|former|ex-|quit|"
    r"discontinued|stopped|resolved)\b", re.I)
_PSEUDO_NEG = re.compile(r"\b(not (well[- ])?controlled|no (change|improvement|worsening)|not responding)\b", re.I)
_NEG_POST = re.compile(r"^[\s,]*(?:\w+\s+){0,2}?(?:was |were |is |has been )?(ruled out|negative|excluded|resolved|"
                       r"discontinued|stopped)\b", re.I)
_SENT_SPLIT = re.compile(r"(?<=[.;!?\n])\s+|\n+")
_CLAUSE_BREAK = re.compile(r"\b(but|however|although|except)\b|[.;:\n]", re.I)


def _is_negated(text: str, start: int, end: int) -> bool:
    # look back to the start of the clause, at most 6 words
    pre = text[max(0, start - 80):start]
    breaks = list(_CLAUSE_BREAK.finditer(pre))
    if breaks:
        pre = pre[breaks[-1].end():]
    window = " ".join(pre.split()[-6:])
    if _NEG_PRE.search(window) and not _PSEUDO_NEG.search(window + " " + text[start:end]):
        return True
    return bool(_NEG_POST.match(text[end:end + 40]))


def _sentence_around(text: str, start: int, end: int) -> str:
    left = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start))
    right_candidates = [i for i in (text.find(".", end), text.find("\n", end), text.find(";", end)) if i != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left + 1:right].strip()


def find_mentions(text: str, kinds: tuple[str, ...] = ("condition", "medication", "lab"),
                  detect_negation: bool = True) -> list[Mention]:
    """Find vocabulary mentions; longer/earlier-kind matches mask overlapping shorter ones."""
    text = normalize_text(text or "")
    masked = text
    mentions: list[Mention] = []
    for kind, pattern, lookup in _KINDS:
        if kind not in kinds:
            continue
        for m in pattern.finditer(masked):
            canonical = lookup[m.group(1).lower()]
            mention = Mention(canonical, kind, m.start(), m.end(), text[m.start():m.end()])
            if detect_negation:
                mention.negated = _is_negated(text, m.start(), m.end())
            mention.sentence = _sentence_around(text, m.start(), m.end())
            mentions.append(mention)
        # mask matched spans so other kinds don't re-match inside them
        for mm in [x for x in mentions if x.kind == kind]:
            masked = masked[:mm.start] + " " * (mm.end - mm.start) + masked[mm.end:]
    mentions.sort(key=lambda x: x.start)
    return mentions


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(normalize_text(text or "")) if len(s.strip()) > 3]


def lab_key_for_name(name: str) -> str | None:
    m = _LAB_RE.search(normalize_text(name or ""))
    return _LAB_LOOKUP[m.group(1).lower()] if m else None
