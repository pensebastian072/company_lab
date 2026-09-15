"""Phase B from the LOCAL filing cache and the LOCAL GPU, with fabrication made impossible.

## Why this exists

Phase B is the plan's whole remaining job: 1,189 of 1,500 companies have an industry expert to be
judged against and no judgement. It was designed around a web-researching agent (Codex), which is
out of budget, and the measured bar it set is steep — the 311 existing rows average **9.6 of 12**
categoricals answered on **17.7 claims per company**, so finishing means roughly **21,000 cited
claims**.

Three facts make a local lane possible:

1. **The filings are already here.** `D:\\company_lab_data\\edgar` holds the 10-K for essentially
   every company in the book, so the evidence needs no network.
2. **The judgement is small and local.** `qwen2.5:7b` runs on the RTX 3050 at 100% on card.
3. **Two of the twelve fields are not research at all.** `market_share_direction` is computed by
   `revenue_share.py` from filed revenue, and `industry_structural_growth` is the SAME SCALE as
   the industry object's `structural_growth` (`schema.FIELD_SYNONYMS` says so) — so it is inherited
   from the expert, which is the entire point of having built 208 of them.

Probed on six packaged-food companies before any of this was written: **6.7 of 9** regex-addressable
fields have a candidate sentence in the filing, which with the two above gives a ceiling near 8.7 of
12 against the existing bar of 9.6.

## The design rule: the model returns an INDEX, never a quote

E40 measured LFM2.5 citing text that is not in the filing **9.7% of the time** (qwen 0.5%). A lane
that asks a model to write a quote inherits that error rate and then has to catch it.

So this lane never asks. Retrieval is deterministic — a field-specific regex over the filing's own
sentences, numbered. The model is given the numbered candidates and must answer with a VALUE and an
`evidence` INDEX. The quote is then taken from the candidate list by that index, verbatim.

**Containment is therefore true by construction, not by checking**, because the sentence came out of
the filing in the first place. It is still asserted afterwards (`verify_claims`), because a guard
that is "obviously" satisfied is exactly the kind this repo has been bitten by.

## What this lane is NOT

It is not a web researcher. Every claim it writes is `SEC_FILING` / `COMPANY_IR` — the company's own
words about itself. That is legitimate for COMPANY fields, which ask what this company's position
and risks are, and it is why the plan's rule 3 (a non-issuer source) is an INDUSTRY-object rule and
not a company one. But it means this lane can never discover anything a filing does not say, and it
will abstain wherever the filing's language is conventional rather than specific.

**Abstention is the designed behaviour, not a shortfall.** `finalize.apply_citation_rule` demotes any
field no claim cites, and `UNKNOWN` scores as `NO_DATA` rather than as a midpoint, so a field this
lane cannot evidence simply stops counting. The failure mode to fear is the opposite one: a model
that answers every field with the same value because every 10-K says "we are subject to extensive
regulation". `acceptance.check_company_batch`'s `constant_fields` check FAILS a rank-order field that
is constant across a batch, which is the guard that catches it — and it is why this module reports
the per-field value spread with every batch rather than only the fill rate.
"""
from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path

from .. import config
from . import schema as S

#: Field -> the pattern that finds sentences capable of evidencing it. Deliberately broad:
#: recall matters here because the model can decline a candidate, but it cannot invent one
#: that retrieval never surfaced. Precision is the model's job and the gate's.
#:
#: `market_share_direction` and `industry_structural_growth` are absent on purpose - the
#: first is computed by revenue_share, the second inherited from the industry object.
#: V1, KEPT ONLY FOR THE A/B in `clab/research/e44_pattern_ab.py`. Not used for
#: scoring. E43 measured what these actually retrieve. Every one selects sentences
#: that mention the field's TOPIC and carry no DEGREE or DIRECTION - a 10-K saying
#: "patent" evidences nothing about moat strength - and `competitive_position` is
#: additionally ONE-SIDED: its pool can only contain assertions of leadership, so it
#: cannot argue that a company is anything else. That is why fields collapsed onto a
#: modal value in BOTH arms, and why LFM contradicted its own citation 53.9% of the
#: time on the one field where that bias made the contradiction visible.
FIELD_PATTERNS_V1: dict[str, str] = {
    "current_moat_strength": (
        r"(our brands?|brand (?:recognition|equity|portfolio)|patent|proprietary|trade "
        r"secret|economies of scale|scale advantage|switching cost|installed base)"),
    "moat_trajectory": (
        r"(continue to invest in our brand|strengthen(?:ing)? our (?:position|brand)|"
        r"erosion|competitive (?:advantage|position) (?:may|could)|renew|expire)"),
    "competitive_position": (
        r"(we are (?:the|a|one of) (?:the )?(?:largest|leading|number one|second largest|"
        r"top)|market leader|leading (?:producer|provider|manufacturer|supplier))"),
    "competitive_position_trend": (
        r"(gain(?:ed|ing)? (?:market )?share|los(?:t|ing) (?:market )?share|share "
        r"(?:gains?|losses?)|grew faster than|outpaced)"),
    "company_specific_capture": (
        r"(productivity|cost sav(?:ings|e)|margin expansion|operating leverage|"
        r"restructuring (?:program|plan)|efficiency)"),
    "demand_visibility": (
        r"(backlog|long-term (?:contracts?|agreements?)|subscription|recurring revenue|"
        r"seasonal|order book|take-or-pay)"),
    "pricing_power": (
        r"(pric(?:e|ing) (?:increases?|actions?)|raise(?:d)? (?:our )?prices|list "
        r"price|pass (?:on|through) (?:cost|increase)|price realisation|realization)"),
    "technology_risk": (
        r"(technological (?:change|advance|development|obsolescence)|new technolog|"
        r"obsolete|automation|artificial intelligence)"),
    "disruption_risk": (
        r"(disrupt\w*|new entrants?|business model|alternative (?:products?|channels?)|"
        r"substitute)"),
    "regulatory_risk": (
        r"(subject to (?:extensive|comprehensive|significant|various|numerous) "
        r"(?:federal|state|local|government|regulat)|regulated by|regulatory "
        r"(?:requirements|approval)|legislation|enforcement action)"),
}

#: V2. Two rules, both consequences of E43:
#:
#:   R1 TWO-SIDED. Every pattern must be able to surface evidence for OPPOSITE ends of its
#:      own vocabulary. A pattern that can only match "we are the largest" guarantees the
#:      pool argues one way, and a spread of answers over such a pool is noise, not
#:      discrimination. Each entry below is written as (high-end | low-end) alternatives.
#:
#:   R2 DEGREE-BEARING. Prefer a sentence carrying a magnitude, a comparative, or an
#:      explicit strength/weakness word over a bare topic mention. "We compete primarily
#:      on price" evidences a weak moat; "patent" evidences nothing.
#:
#: Recall still matters more than precision - the model can decline a candidate but cannot
#: invent one retrieval never surfaced - so these stay broad. What they must not stay is
#: one-sided.
#:
#: `market_share_direction` and `industry_structural_growth` are absent on purpose - the
#: first is computed by revenue_share, the second inherited from the industry object.
FIELD_PATTERNS: dict[str, str] = {
    # V1's alternatives, PLUS the missing pole, MINUS only what E43 measured to be junk.
    # The first V2 draft rewrote these from scratch and E44's A/B refused it: two-sidedness
    # rose but moat_trajectory's pool fell from 300 companies to 40. Recall matters more
    # than precision here - the model can decline a candidate but cannot invent one that
    # retrieval never surfaced - so the repair ADDS a low end rather than narrowing a high
    # one. Each `# +low` block is the pole V1 could not express.
    "current_moat_strength": (
        r"(our brands?|brand (?:recognition|equity|portfolio)|patent|proprietary"
        r"|trade secret|economies of scale|scale advantage|switching cost|installed base"
        # +low: commodity economics, stated as fact
        r"|highly commoditi\w+|commodity (?:product|business|market)"
        r"|compete (?:primarily |largely |principally )?on (?:the basis of )?price"
        r"|price is (?:the|a) (?:primary|principal|key) (?:factor|consideration)"
        r"|low switching costs?|no (?:significant |material )?barriers to entry"
        r"|patents? (?:expire|expiring|will expire))"
    ),
    "competitive_position": (
        # The bare `leading (producer|provider|manufacturer|supplier)` alternative is
        # REMOVED: E43 found it matching "products from leading suppliers" and "acquired
        # Traverse Systems, an industry-leading firm" - leadership belonging to somebody
        # else, scored as if it belonged to the filer.
        r"(we are (?:the|a|one of) (?:the )?(?:largest|leading|number one|second largest|top)"
        r"|market leader|we (?:are|remain) a leading (?:producer|provider|manufacturer|supplier)"
        r"|we rank(?:ed)? (?:first|second|third|among)"
        # +low: the filer placing itself BELOW its competitors, stated as fact
        r"|(?:many|some|certain|most) of our competitors (?:are|have|possess)"
        r"|our competitors (?:are|have) (?:greater|larger|more|substantially)"
        r"|we compete (?:against|with) (?:larger|companies (?:that|which) are larger)"
        r"|we are (?:a )?(?:smaller|small) (?:participant|player|competitor))"
    ),
    "competitive_position_trend": (
        r"(gain(?:ed|ing)? (?:market )?share|los(?:t|ing) (?:market )?share"
        r"|share (?:gains?|losses?)|grew faster than|outpaced"
        # +low
        r"|grew (?:more )?slow(?:ly|er) than|underperformed the (?:market|industry)"
        r"|(?:volumes?|revenues?) declined|trailed the (?:market|industry))"
    ),
    "moat_trajectory": (
        # `renew|expire` REMOVED - it matched lease and contract boilerplate in every
        # filing, which is why this field read STABLE for 94% of LFM's book. Everything
        # else V1 had is kept, because narrowing this one cost 260 of 300 pools.
        r"(continue to invest in our brand|strengthen(?:ing|ed)? our (?:position|brand)"
        r"|competitive (?:advantage|position)|expanded our (?:lead|share|advantage)"
        r"|brand (?:strength|loyalty)|renewal rates?"
        # +low
        r"|erosion|eroded|commoditi\w+|increased competition|churn"
        r"|(?:advantage|position) (?:has )?(?:narrowed|declined|weakened)"
        r"|patents? (?:expire|expiring|will expire) in)"
    ),
    "company_specific_capture": (
        r"(productivity|cost sav(?:ings|e)|margin expansion|operating leverage"
        r"|restructuring (?:program|plan)|efficiency"
        # +low
        r"|margin (?:compression|contraction)|margins? declined|cost inflation"
        r"|unable to offset|deleverage)"
    ),
    "demand_visibility": (
        r"(backlog|long-term (?:contracts?|agreements?)|subscription|recurring revenue"
        r"|seasonal|order book|take-or-pay|deferred revenue"
        # +low
        r"|no (?:material )?backlog|short(?:er)? (?:order|lead) (?:cycle|time)"
        r"|book[- ]and[- ]ship|spot (?:market|sales|pricing))"
    ),
    "pricing_power": (
        r"(pric(?:e|ing) (?:increases?|actions?)|raise(?:d)? (?:our )?prices|list price"
        r"|pass (?:on|through) (?:cost|increase)|price realisation|realization"
        # +low - V1 could only ever surface evidence of pricing STRENGTH
        r"|pricing pressure|price competition|unable to pass|price (?:erosion|declines?)"
        r"|competitive pricing|discount\w+ to)"
    ),
    "technology_risk": (
        r"(technological (?:change|advance|development|obsolescence)|new technolog"
        r"|obsolete|automation|artificial intelligence"
        # +low: technology stability stated as fact. E44 measured BOTH V1 and the first V2
        # draft at 0.0 two-sidedness here, so these markers are on probation - if the next
        # A/B still reads 0.0, this field is one-sided in the filings themselves and no
        # pattern fixes it.
        r"|long product life cycles?|mature technolog\w+|stable technolog\w+"
        r"|(?:our )?technology (?:has|is) (?:not )?(?:changed|stable))"
    ),
    "disruption_risk": (
        # `business model` REMOVED - it matched every filing's strategy section.
        r"(disrupt\w*|new entrants?|alternative (?:products?|channels?)|substitute"
        r"|changing (?:consumer|customer) preferences"
        # +low
        r"|high barriers? to entry|few new entrants|limited substitutes?"
        r"|significant barriers to entry)"
    ),
    "regulatory_risk": (
        r"(subject to (?:extensive|comprehensive|significant|various|numerous)"
        r" (?:federal|state|local|government|regulat)|regulated by"
        r"|regulatory (?:requirements|approval)|legislation|enforcement action"
        # +high: regulation with TEETH, which the boilerplate alternative cannot express
        r"|consent decree|civil penalt|fined|fines? of|license\w* (?:revoked|suspended)"
        r"|rate (?:case|regulation)"
        # +low
        r"|not subject to (?:material |significant )?regulation)"
    ),
}

#: Sentences that CANNOT evidence a current state, however well they match a field's
#: pattern. Added after the first probe, which produced these four claims among others:
#:
#:   competitive_position_trend = DETERIORATING  <- "could result in ..."        (CAG)
#:   company_specific_capture   = MODERATE       <- "We cannot guarantee ..."    (CAG)
#:   pricing_power              = MODERATE       <- "is expected in fiscal 2026" (HRL)
#:   moat_trajectory            = STABLE         <- "we do not believe that our
#:                                                   businesses are materially
#:                                                   dependent upon [patents]"   (GIS)
#:
#: The first three are a RISK FACTOR or GUIDANCE being read as an observation. A 10-K's
#: risk factors are a list of things that have NOT happened, written to be exhaustive
#: rather than probable, and treating "a competitor could respond strongly" as evidence
#: that this company's position IS deteriorating inverts the document's own meaning.
#:
#: This is the same standard applied to the industry objects earlier the same day, where
#: Aptiv's forward expectation was refused as evidence because it was not a measured
#: quantity. A lane that accepts it for companies while refusing it for industries would
#: hold two standards at once.
#:
#: Recall is the cost and it is accepted: a field with no unconditional sentence is a
#: field this lane abstains on, and abstention scores as NO_DATA rather than as a guess.
EXCLUDE_MARKERS: tuple[str, ...] = (
    "could ", "may adversely", "may be adversely", "may not ", "might ", "would likely",
    "we cannot guarantee", "cannot assure", "no assurance", "there can be no",
    "risk that", "if we fail", "if we are unable", "failure to ",
    "is expected", "are expected", "we expect", "we anticipate", "outlook for",
    "guidance", "forward-looking", "we believe that our businesses are not",
    "do not believe",
)


def _is_hypothetical(sentence: str) -> bool:
    """True when the sentence describes a possibility rather than a state."""
    low = sentence.lower()
    return any(m in low for m in EXCLUDE_MARKERS)


#: Sentence length window. Below this a fragment carries no argument; above it the
#: "sentence" is almost always a table or a run-on that the extractor failed to split, and
#: a 900-character quote is unreadable in the workbook the user actually opens.
MIN_SENT, MAX_SENT = 60, 300

#: Candidates offered per field. Enough for the model to have a real choice, few enough
#: that the prompt stays inside a 7B model's useful attention span.
MAX_CANDIDATES_PER_FIELD = 6


@dataclass
class Filing:
    ticker: str
    cik: str
    url: str
    filed: str
    text: str
    #: Which form actually backed this row. A 10-Q is NOT equivalent evidence to a 10-K -
    #: it carries no full business description and usually no risk factors - so a consumer
    #: must be able to tell them apart rather than inferring "a filing is a filing".
    form: str = "10-K"


@dataclass
class CompanyResult:
    ticker: str
    filing: Filing | None = None
    categoricals: dict[str, str] = dc_field(default_factory=dict)
    claims: list[dict] = dc_field(default_factory=list)
    abstained: list[str] = dc_field(default_factory=list)
    notes: list[str] = dc_field(default_factory=list)


def load_filing(ticker: str, cik: str | None, form: str = "10-K") -> Filing | None:
    """The newest cached filing of `form` for this company, as plain text.

    Returns None rather than raising: a company with no cached filing is a company this
    lane cannot research, which is a reportable state and not an error.
    """
    if not cik:
        return None
    c = str(cik).zfill(10)
    sub = config.EDGAR_SUBMISSIONS_DIR / f"CIK{c}.json.gz"
    if not sub.exists():
        return None
    js = json.loads(gzip.open(sub, "rt", encoding="utf-8", errors="replace").read())
    recent = js.get("filings", {}).get("recent", {})
    for f, acc, date, doc in zip(recent.get("form", []), recent.get("accessionNumber", []),
                                 recent.get("filingDate", []),
                                 recent.get("primaryDocument", [])):
        if f != form:
            continue
        path = config.EDGAR_FILINGS_DIR / c / f"{acc}.txt.gz"
        if not path.exists():
            continue
        raw = gzip.open(path, "rt", encoding="utf-8", errors="replace").read()
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(c)}/"
               f"{acc.replace('-', '')}/{doc}")
        return Filing(ticker, c, url, date, text, form)
    return None


def candidates(text: str, patterns: dict[str, str] | None = None) -> dict[str, list[str]]:
    """Field -> candidate sentences from the filing, deduplicated, order preserved.

    Sentences are split on a period followed by whitespace. That is crude and it is
    deliberate: a smarter splitter would rewrite the text, and the whole point is that
    every candidate is a verbatim slice of the filing so the quote cannot drift.
    """
    sents = [s.strip() for s in re.split(r"(?<=\.)\s+", text)]
    sents = [s for s in sents if MIN_SENT <= len(s) <= MAX_SENT]
    out: dict[str, list[str]] = {}
    for field, pat in (patterns or FIELD_PATTERNS).items():
        rx = re.compile(pat, re.I)
        seen: set[str] = set()
        picked: list[str] = []
        for s in sents:
            if len(picked) >= MAX_CANDIDATES_PER_FIELD:
                break
            if not rx.search(s):
                continue
            if _is_hypothetical(s):
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            picked.append(s)
        if picked:
            out[field] = picked
    return out


def prompt_for(ticker: str, name: str, field: str, cands: list[str]) -> str:
    """One field, one company, numbered candidates, an index for an answer.

    One field per call rather than twelve in one: a 7B model asked for twelve
    simultaneous judgements returns a plausible dict with the same value repeated, which
    is precisely the constant-field failure `acceptance.constant_fields` exists to catch.
    """
    vocab = [v for v in S.VOCABULARIES[field] if v != S.UNKNOWN]
    numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(cands))
    return (
        f"You are reading {name} ({ticker})'s own 10-K to answer ONE question.\n\n"
        f"QUESTION: what is this company's {field.replace('_', ' ')}?\n"
        f"ALLOWED ANSWERS: {', '.join(vocab)}, or UNKNOWN.\n\n"
        f"Sentences from the filing:\n{numbered}\n\n"
        f"Rules:\n"
        f"- Choose the answer the sentences SUPPORT. If they do not support any answer, "
        f"answer UNKNOWN.\n"
        f"- Cite ONE sentence by its number. Never write the sentence out.\n"
        f"- Boilerplate that every company files (\"we are subject to extensive "
        f"regulation\") supports only a MODERATE reading at most; reserve the extreme "
        f"values for specific, quantified statements.\n\n"
        f'Reply with JSON only: {{"value": "<one allowed answer>", "evidence": <number>, '
        f'"why": "<at most 20 words>"}}')


def parse_judgement(raw: str, field: str, n_cands: int) -> tuple[str, int | None, str]:
    """(value, evidence index, why). Returns UNKNOWN on anything malformed.

    An out-of-range index or an off-vocabulary value is treated as an abstention rather
    than repaired. Repairing it would invent a judgement the model did not make, which is
    the `extract_json` bug from the v2 lane in a new costume: that one silently turned
    real scores into NULLs, and the lesson was to fail visibly.
    """
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return S.UNKNOWN, None, "no json"
    try:
        d = json.loads(m.group(0))
    except Exception:
        return S.UNKNOWN, None, "bad json"
    value = str(d.get("value", "")).strip().upper().replace(" ", "_")
    if value not in S.VOCABULARIES.get(field, ()):
        return S.UNKNOWN, None, f"off-vocabulary: {value!r}"
    idx = d.get("evidence")
    why = str(d.get("why", ""))[:200]
    if value == S.UNKNOWN:
        return S.UNKNOWN, None, why
    if not isinstance(idx, int) or not (0 <= idx < n_cands):
        return S.UNKNOWN, None, f"evidence index out of range: {idx!r}"
    return value, idx, why


def claim_for(ticker: str, field: str, value: str, quote: str, why: str,
              filing: Filing) -> dict:
    import hashlib
    cid = "c_" + hashlib.sha1(
        f"PB|{ticker}|{field}|{quote}".encode()).hexdigest()[:12]
    return {
        "claim_id": cid,
        "ticker": ticker,
        "field": field,
        "value": value,
        "text": (f"{ticker}: {field} = {value}. Selected by the local scorer from "
                 f"sentences extracted from the company's own {filing.filed} 10-K; the "
                 f"model chose this sentence by index and did not write it, so the quote "
                 f"is a verbatim slice of the filing. Model's reason: {why or 'none given'}"),
        "quote": quote,
        "source_url": filing.url,
        "source_title": f"{ticker} 10-K",
        "source_date": filing.filed,
        "source_type": "SEC_FILING",
        "independence_domain": "COMPANY_IR",
        "stance": "SUPPORTS",
        "fact_or_inference": "INFERENCE",
    }


#: Deterministic contradiction rules: (field) -> (predicate on the cited sentence, the
#: values that sentence REFUTES). No model is involved and none may be.
#:
#: E43 measured LFM2.5 answering LAGGARD while citing "We are a leading global provider of
#: security products" - 53.9% of its checkable competitive_position claims contradicted
#: their own quote, against qwen's 0.0%. The model cannot fabricate a quote in this
#: harness (it cites by index), so this is the failure mode that IS available to it, and
#: it is catchable without any ground truth: if the only sentence offered says the filer
#: leads its market, LAGGARD is wrong on the model's own stated evidence.
#:
#: A contradicted claim becomes an ABSTENTION, never a corrected answer. Rewriting LAGGARD
#: to LEADER would be the gate inventing judgement it has no basis for - the sentence
#: establishes that the model misread, not what the right reading is.
#:
#: Only rules with a written argument belong here. Each one must be able to fire AND to
#: not fire; `tests/test_contradiction_gate.py` pins both directions.

#: The filer asserting its OWN leadership. Narrower than the retrieval pattern on purpose:
#: "products from leading suppliers" and "acquired an industry-leading firm" are claims
#: about OTHER companies and evidence nothing about the filer, so they must not fire.
_SELF_LEADER = re.compile(
    r"\b(?:we are|we're|the company is|we remain|we have been)\s+"
    r"(?:the\s+|a\s+|one of\s+(?:the\s+)?)?"
    r"(?:world'?s\s+|nation'?s\s+|global\s+|leading\s+|largest\s+|premier\s+|top\s+|"
    r"market[- ]leading\s+|number one\s+|second[- ]largest\s+)",
    re.I)
_OTHER_LEADER = re.compile(
    r"\b(?:from|with|by|of)\s+(?:the\s+)?(?:world'?s\s+)?leading\b"
    r"|\ban industry[- ]leading\b|\bleading (?:suppliers|vendors|customers|partners)\b",
    re.I)


def _cites_own_leadership(quote: str) -> bool:
    return bool(_SELF_LEADER.search(quote)) and not bool(_OTHER_LEADER.search(quote))


#: field -> (predicate, refuted values)
CONTRADICTION_RULES: dict[str, tuple] = {
    "competitive_position": (_cites_own_leadership, frozenset({"LAGGARD", "CHALLENGER"})),
}


def contradicts(field: str, value: str, quote: str) -> str | None:
    """Reason the cited sentence refutes this value, or None.

    Deterministic and cheap enough to run at ingest over any book, including the 311
    Codex rows that no local model ever touched.
    """
    rule = CONTRADICTION_RULES.get(field)
    if not rule or not quote:
        return None
    predicate, refuted = rule
    if str(value).upper() in refuted and predicate(quote):
        return (f"{field}={value} is refuted by the sentence it cites, in which the "
                f"company asserts its own market leadership")
    return None


def verify_claims(result: CompanyResult) -> list[str]:
    """Assert every quote really is in the filing. Should be vacuous; is not skipped.

    Containment is true by construction here - the quote was sliced out of the filing
    text. This checks it anyway, because "obviously satisfied" is how the four graceful-
    degradation bugs of 2026-08-13 all read before they were found.
    """
    if not result.filing:
        return ["no filing"]
    hay = re.sub(r"\s+", " ", result.filing.text).lower()
    bad = []
    for c in result.claims:
        if re.sub(r"\s+", " ", c["quote"]).strip().lower() not in hay:
            bad.append(f"{c['field']}: quote not in the filing it cites")
    return bad


def schema_for(field: str, n_cands: int) -> dict:
    """Ollama `format` schema for one field's answer.

    Structured output is not a nicety here. `clab/qual/ollama.chat`'s own docstring
    records LFM2.5 emitting 3,417 characters of reasoning and being truncated before any
    JSON - a 77.8% "parse failure" rate that was a format artefact rather than a failure
    of judgement. Constraining generation makes a prose preamble, a missing key and a
    malformed object structurally impossible.

    `evidence` is an INTEGER and `value` is an ENUM of this field's own vocabulary, so the
    model cannot answer off-vocabulary and cannot hand back a quote even if it tries.
    UNKNOWN stays in the enum because an abstention must remain expressible - a schema
    that forced a real value would convert every honest abstention into a fabricated one.
    """
    return {
        "type": "object",
        "properties": {
            "value": {"type": "string", "enum": list(S.VOCABULARIES[field])},
            "evidence": {"type": "integer", "minimum": 0,
                         "maximum": max(n_cands - 1, 0)},
            "why": {"type": "string"},
        },
        "required": ["value", "evidence"],
    }
