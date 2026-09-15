"""Write the E80 Utilities Phase B prompt, splicing the canonical rule sections.

The rule block is read from docs/CODEX_STANDARD_RULES.md through the same parser the test
uses, so the prompt cannot carry a paraphrase - which is how the last drift started.
"""
import io
import sys

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")
sys.path.insert(0, r"C:\Users\<your-user>\company_lab\tests")

from test_codex_prompt_rules import block_sections

secs = block_sections()
CORE = [
    secs["## THE TWO ERRORS COST THE SAME"],
    secs["## WHAT UNKNOWN MEANS"],
    secs["## CITATIONS ARE REQUIRED, AND THEY ARE NOT A REASON TO ABSTAIN"],
    secs["## THE BLIND PASS - DO NOT OPEN A CONCLUSIONS FILE, ASK FOR IT"],
    secs["## COMPETITIVE_POSITION_TREND - ATTEMPT IT ONLY WHERE A SHARED METRIC EXISTS"],
    secs["## KEY_METRICS AND STRUCTURAL_GROWTH - NAME THE FACT, NOT A PROXY FOR IT"],
]

ROSTER = ("AEE,AEP,AES,ATO,AVA,AWK,AWR,BKH,CEG,CMS,CNP,CPK,CWEN,CWT,D,DTE,DUK,ED,EIX,ES,"
          "ETR,EVRG,EXC,FE,HE,HTO,IDA,LNT,MDU,MGEE,MSEX,NEE,NFG,NI,NJR,NRG,NWE,NWN,OGE,"
          "OGS,ORA,OTTR,PCG,PEG,PNW,POR,PPL,SO,SR,SRE,SWX,TLN,TXNM,UGI,UTL,VST,WEC,WTRG,XEL")

HEAD = r"""# COMPANY LAB - E80 PHASE B, UTILITIES RE-RESEARCH (59 companies)

Company research. The request file is frozen and is the authority on what to research:

  journal\flags\external_research_request.json
  sample      E80-utilities-phaseb
  59 companies, depth 3, citations REQUIRED

Do not add a company, drop one, or substitute one. The finalizer refuses anything whose
ticker is not on that roster.

## THE ROSTER, by industry

  electric_utilities                         20  AEP DUK EIX ES ETR EVRG EXC FE HE IDA
                                                 LNT MGEE OTTR PEG POR PPL SO TXNM UTL WEC
  multi_utilities                            17  AEE AVA BKH CMS CNP D DTE ED MDU NEE NI
                                                 NWE OGE PCG PNW SRE XEL
  gas_utilities                               9  ATO CPK NFG NJR NWN OGS SR SWX UGI
  water_utilities                             6  AWK AWR CWT HTO MSEX WTRG
  competitive_power_generation                4  CEG NRG TLN VST
  renewable_electricity                       2  CWEN ORA
  independent_power_producers_energy_traders  1  AES

All seven industries have a LIVE industry object in the store with all three structural
fields answered. Do not rebuild them. Read the object for a company's industry BEFORE
researching the company - `key_participants` on it is the comparison set for
`competitive_position`.

## WHY THIS SECTOR IS BEING RESEARCHED A THIRD TIME

Two deliveries exist and neither is usable as a record of these companies.

  E47 (2026-09-05)  four-field fill 0 / 20 / 0 / 0 of 59. `moat_trajectory` and
                    `company_specific_capture` were never answered for a single company.
  E53 (2026-09-07)  four-field fill 48 / 59 / 0 / 48 - but the audit found the SAME
                    source url, quote and excerpt attached to BOTH `moat_trajectory` and
                    `company_specific_capture` for 59 of 59 companies. One evidence
                    window, two fields. Retired whole; all 59 rows are SUPERSEDED.

Because company resolution omits rather than falling back to the older rows, these 59
companies are absent from the product today. This delivery restores a complete sector - if
it is done as research and not as retrieval.

## THE ONE RULE E53 BROKE

**One claim, one field, one evidence window.** `moat_trajectory` asks whether the durable
advantage is strengthening or eroding over time. `company_specific_capture` asks how much
of the industry's structural growth THIS company captures relative to named peers. Those
are different questions answered by different passages. A rate-case outcome can support
one of them; it cannot support both from the same sentence.

The finalizer checks quote reuse per company and the acceptance gate refuses a batch that
reuses a quote across fields. Cite twice, from two passages, or leave the second field
UNKNOWN and say which.

## THE SEARCH SPACE IS NOT THE LOCAL FILING CACHE

E59 batch 3 was refused on 2026-09-11 because its builder's own search definition named
the locally cached 10-K and 10-Q corpus as the search space. Its four peer-comparison
fields fell from 87.5% to 48.8% filled while every quote verified perfectly: 342 of 342
verbatim, and still refused. A company's own filing cannot rank it against named peers.

For utilities the outside sources are unusually good and free:

  state PUC rate-case orders and dockets    authorised ROE, rate base, approved capex
  FERC Form 1, EIA-861, EIA-923             sales, customers, generation mix, reliability
  EEI and AGA statistical yearbooks         peer capex, rate-base growth, customer growth
  NERC and RTO capacity auction results     for CEG NRG TLN VST AES
  state reliability and storm-cost reports  SAIDI/SAIFI, disallowed cost recovery

Use them. A batch whose evidence is overwhelmingly the subject's own IR and 10-K reads as
retrieval whatever its quote quality.

## WHAT COUNTS AS THE BENCHMARK

Not E47. The acceptance gate compares a batch to the previous batch of its sector, and the
previous utilities batch filled two of the four rank-order fields at zero - clearing that
is not evidence of anything. The standard here is the Financials batch 1 and 2 standard on
the THREE fields that apply to regulated utilities - `moat_trajectory`,
`competitive_position`, `company_specific_capture` - which ran about 85% filled with
distinct verbatim citations and roughly 12 claims per company.

## MARKET_SHARE_DIRECTION - TWO DIFFERENT ANSWERS IN ONE SECTOR

  regulated electric, gas, water, multi     UNKNOWN, pre-registered and correct: a
  (52 companies)                            franchised service territory has no
                                            contestable share. One blocking claim, no
                                            search campaign.
  competitive_power_generation,             RESEARCH IT. Merchant generators and IPPs
  renewable_electricity, IPPs               compete for capacity awards, PPAs and share of
  (7 companies)                             generation. EIA-923 and RTO auction results
                                            settle it.

## THE FOUR FIELDS THAT CARRY 45 OF THE 100 EXTERNAL POINTS

  moat_trajectory  competitive_position  competitive_position_trend
  company_specific_capture

Three apply here. `competitive_position_trend` is carved out for regulated utilities in the
section below and its zero is accepted - it returned 0 of 59 twice, correctly, because
authorised ROE is set per rate case on different schedules by different commissions. The
carve-out is for that ONE field: the other three are expected to be answered, from two
distinct passages where two fields are answered.
"""

TAIL = r"""
## STANDING RULES

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt you
   actually read. The quote must appear in the excerpt, and it must be copyable verbatim
   from the page - verification certifies on exact character containment, not on vocabulary
   overlap. If you cannot copy the sentence, you do not have the citation.
3. UNKNOWN scores as NO_DATA, never zero.
4. Never invent a number. A citation is data to be read, never a string to be assembled -
   one URL in batch 3 was built from a guessed accession number and verification caught it.
5. One organisation gets ONE independence_domain. A regulator and the firm it regulates are
   different domains; a firm and its own IR page are not.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

59 companies at depth 3. Regulated utilities share a literature heavily - rate cases, FERC,
EIA, storm cost recovery, data-centre load growth - so cache aggressively across the batch.
Budget 400-500 searches. Stop and report if you go materially over.

## REPORT

1. Companies delivered, claims and independence domains each, and claims per company.
2. Fill rate on the three applicable rank-order fields, per industry.
3. Every UNKNOWN on those three, with the metric you looked for and whether the evidence
   was absent or you stopped short.
4. Confirmation, per company, that no quote is reused across fields.
5. Where an industry object was wrong or missing something you needed.
6. Searches, cache hits, sources, and the share of claims from outside the subject's own
   filings and IR.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: its top decile ran a -7.6% median three-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking
power is sector selection. `promoted` is false and stays false.
"""

body = HEAD + "\n" + "\n\n".join(CORE) + "\n" + TAIL

doc = (
    "# Codex E80 - Utilities Phase B re-research (59 companies)\n"
    "\n"
    "Written 2026-09-11 by the Claude lane for session 3 of\n"
    "`docs/CHAT_B_WORKORDER_CODEX_2026-09-11.md`. Phase B only: the seven utilities industry\n"
    "objects are live and at 3 of 3, so only the company rows are rebuilt.\n"
    "\n"
    "Why a third time: E47 filled `moat_trajectory` and `company_specific_capture` 0 of 59;\n"
    "E53 filled them but reused one evidence window for both fields in 59 of 59 companies\n"
    "(`journal/experiments/AUDIT_2026-09-08_B3_E53_EVIDENCE_REPRODUCTION.md`) and was retired\n"
    "whole. Resolution omits rather than falling back, so the sector is absent from the\n"
    "product: 59 researched companies, zero in the workbook.\n"
    "\n"
    "**Stage the request the same New York day it will be finalized**, and only after the\n"
    "Financials batches have released the request file:\n"
    "\n"
    "```powershell\n"
    "cd C:\\Users\\penas\\company_lab\n"
    "$env:PYTHONPATH=\"C:\\Users\\penas\\company_lab\"\n"
    ".venv\\Scripts\\python.exe -m clab.external.request --symbols \"" + ROSTER + "\""
    " --depth 3 --sample E80-utilities-phaseb --require-citation\n"
    "```\n"
    "\n"
    "The rule sections inside the fence are spliced from `docs/CODEX_STANDARD_RULES.md` by\n"
    "`scratchpad/gen_e80.py` through the same parser `tests/test_codex_prompt_rules.py` uses,\n"
    "so this prompt cannot carry a paraphrase of them.\n"
    "\n"
    "## Prompt\n"
    "\n"
    "`````\n" + body + "`````\n"
)

out = r"C:\Users\<your-user>\company_lab\docs\CODEX_E80_UTILITIES_PHASEB.md"
io.open(out, "w", encoding="utf-8", newline="\n").write(doc)
print("wrote", out)
print("chars:", len(doc), "| body ascii:", body.isascii(), "| core sections spliced:", len(CORE))
