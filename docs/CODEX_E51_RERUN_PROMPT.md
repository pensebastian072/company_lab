# Codex E51 — Communication Services, re-run with the incentive fixed

Same 47 companies as E49. Same industry objects — **do not rebuild them.** The only thing
that changes is the rules block.

## What this is

E49 returned 47 of 47 companies, 564 of 564 claims `VERIFIED_LOCAL`, zero rejections and
zero demotions — and **0 of 47 companies carried any of the four fields that need a
comparison against named peers.** Those four are worth 45 of the 100 external points.

Measured across eight batches, those fields went 92%, 83%, 87%, 49%, 65%, 30%, 8%, 0%
filled. Holding the industry fixed, `upstream_oil_gas` ran 92%, then 38%, then 5%. The
industries did not change.

The likely cause is in the prompts I wrote, not in the research. From E44 onward every one
of them carried "zero demotions — hold that" and "an UNKNOWN with blocking claims is a
RESULT". That rewards abstention and penalises assertion, and I repeated the streak back
each batch. E51 removes it and measures what happens.

**Codex is not being told it did anything wrong.** It followed the instructions it was
given. The instructions were the problem.

## The request

`cb5a414ee0f1d181394b`, 47 companies, depth 3, `require_citation` ON.
`journal/flags/external_research_request.json`.

The 11 Communication Services industry objects already exist and are current. Read them,
do not rebuild them. There is no Phase A.

The id does not expire; the timestamp does. `generated_at` is not in the content hash, so
rebuilding this roster reproduces `cb5a414ee0f1d181394b` exactly.

## Prompt

`````
# COMPANY LAB — E51: COMMUNICATION SERVICES, RE-RUN

Request: C:\Users\<your-user>\company_lab\journal\flags\external_research_request.json
request_id cb5a414ee0f1d181394b. Echo it verbatim. The roster is frozen.

The same 47 companies you researched as E49. The 11 industry objects already exist and
are current - READ them, do not rebuild them. There is no Phase A.

  D:\company_lab_data\external\research\industries\<industry_id>\industry_state.json
  D:\company_lab_data\external\research\sectors\communication_services\sector_state.json

## WHY YOU ARE DOING THIS AGAIN

Not because the last run was careless. It was not: 47 of 47 accepted, 564 of 564 claims
verified locally, zero rejections, zero demotions.

Because four fields came back UNKNOWN for all 47 companies -

  moat_trajectory, competitive_position, competitive_position_trend,
  company_specific_capture

- and those four are 45 of the 100 points we compute. Across eight batches they went from
92% filled to 0% filled while every quality metric stayed perfect. Holding the industry
fixed, upstream_oil_gas ran 92%, then 38%, then 5%.

The cause is probably the prompts. They kept telling you that a well-blocked UNKNOWN was a
success and that an uncited assertion was a failure, and they kept congratulating the
streak. That is a one-sided incentive and it was ours, not yours. It has been removed.

## THE TWO ERRORS COST THE SAME

There are two ways to be wrong here and they are equally bad.

  ASSERTING what you cannot evidence.   A categorical with no claim naming that field is
                                        removed by the finalizer. It corrupts the score
                                        and it wastes the search that produced it.

  ABSTAINING when you could have        An UNKNOWN on a field that the evidence would
  established it.                       have supported is a silent loss. It costs the
                                        company real points - the score divides by what
                                        APPLIES, not by what you answered - and unlike a
                                        bad assertion nothing in the pipeline catches it.

Neither is the safe choice. UNKNOWN is not a way to avoid being wrong; it is a different
way to be wrong, and it is the one that leaves no trace.

For every field you leave UNKNOWN, say in the report which you were closer to: was the
evidence genuinely absent, or did you stop short? An honest "I stopped short" is more
useful to us than a confident blocking claim, and it costs you nothing.

## WHAT UNKNOWN MEANS

UNKNOWN means the evidence to establish this field does not exist or could not be
reached. It does NOT mean:

  - the answer is uncertain          -> give the answer your evidence supports
  - the answer is mid-range          -> MODERATE and STABLE are real values, use them
  - peers are hard to compare        -> say so AND give your best-evidenced reading
  - the field feels risky to answer  -> that is the abstention error, see above

UNKNOWN scores as NO_DATA and never as zero, so it does not drag a company down relative
to its peers. That is exactly why it is tempting and exactly why it must be earned.

## CITATIONS ARE REQUIRED, AND THEY ARE NOT A REASON TO ABSTAIN

Every non-UNKNOWN categorical needs a claim whose `field` names it. That rule exists to
stop unbacked assertion, NOT to discourage answering. If you can evidence a field, cite
it and answer it. If the citation requirement is what is stopping you from answering a
field you believe you could establish, say so explicitly in the report - that is a
finding about our process and we want it.

## THE FOUR FIELDS THIS RUN IS ABOUT

  competitive_position         LAGGARD | CHALLENGER | STRONG_NUMBER_TWO | LEADER | DOMINANT
  competitive_position_trend   DETERIORATING | STABLE | IMPROVING
  moat_trajectory              DETERIORATING | WEAKENING | STABLE | STRENGTHENING
  company_specific_capture     NONE | LOW | MODERATE | HIGH

`competitive_position` in particular should rarely be UNKNOWN in this sector. GOOGL's
position in search, META's in social, NFLX's in streaming and TMUS's in wireless are
documented in their own filings, their competitors' filings, and regulatory proceedings.
If a company genuinely cannot be placed against its named peers, say what blocked it -
but do not leave a documented leader unplaced.

For `competitive_position_trend`, use rank-order against the named peers in the industry
object on a shared metric over the same two periods. Candidates in this sector: ARPU, DAU
or MAU growth, subscriber net adds, churn, retransmission revenue per subscriber, organic
revenue growth, take rate.

## STILL COMPUTED - DO NOT RESEARCH

market_share_direction, company size, and growth versus peers are all computed here from
filed revenue. Leave market_share_direction UNKNOWN with "computed from revenue share".
Do not spend searches on how large a company is or how fast it grew relative to peers.

## THE QUESTION THIS SYSTEM EXISTS TO ANSWER

Three companies can look identical in the accounts: a moat that is STRONG, one that is
STRENGTHENING, and one that still reads strong in the financials but is DETERIORATING
underneath. Only the third is dangerous, and the financial history cannot separate them.

This sector's version: an audience is not a moat, and the accounts cannot tell the
difference between a business that owns its distribution and one that rents it. A company
whose traffic comes from search referral, an app store, or a platform's recommendation
algorithm reports the same revenue as one that owns the relationship, right up until the
referral stops.

## THE REST, UNCHANGED

Twelve fields, closed vocabularies, `cheapness_quality` retired. Risk fields peer-relative
- a company must be worse than its INDUSTRY peers for a flag to fire.

TWO PASSES. Pass A blind; CHTR carries no filing evidence, a gap in our half. Then ask for
journal\flags\external_research_conclusions.json and add pass_b.reconciliation per
disagreement. Do not rewrite pass A.

SELF-CHECK before reporting:
  .venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\cb5a414ee0f1d181394b.json

STANDING RULES
1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt.
3. UNKNOWN scores as NO_DATA, never zero.
4. Never invent a number.
5. One organisation gets ONE independence_domain for the whole record.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

BUDGET: 250-350 searches. The industry objects are already built.

## REPORT

1. Per company: fields backed, fields UNKNOWN.
2. **For every UNKNOWN: "evidence absent" or "stopped short".** This is the headline of
   the run.
3. The four fields above: how many resolved, and on what evidence.
4. Any field where the citation requirement stopped you answering something you believed
   you could establish.
5. Claims, sources, independence domains, searches, cache hits.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return against
SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking power is
sector selection. `promoted` is false and stays false.
`````

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\cb5a414ee0f1d181394b.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.revenue_share --sector communication_services --apply-to "<version>"
.venv\Scripts\python.exe -m clab.external.score --version "<version>" --apply
.venv\Scripts\python.exe -m clab.external.batch_health --version "<version>"
```

Then evaluate E51's five registered predictions. **Utilities is not re-run until this
reports** — re-running 59 more companies before knowing whether the change works is the
mistake the pre-registration exists to avoid.
