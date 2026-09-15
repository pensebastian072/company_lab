# External-source verification correction - 2026-09-07

ADVISORY / SHADOW. This corrects the verification count; it does not promote or
invalidate a research batch, and it does not replace any historical result.

The earlier corpus figure of **4 UNVERIFIABLE out of 5,225 checked (0.077%)** was
computed before the verifier made source extraction state and quoted numbers explicit.
The source cache intentionally stores original bytes. PDF bytes are now required to
produce plausible extracted text before a claim can verify, raw `%PDF` input cannot be
passed to the quote matcher, and the token-overlap fallback can no longer substitute
different numbers for the values in a quotation.

Focused re-verification used PDF magic rather than URL suffix. The current cache held
**23 PDF sources cited by 272 quoted claims** (the fix-pass estimate of 24 sources and
156 claims had drifted as the corpus grew):

| Outcome | Claims |
|---|---:|
| VERIFIED_LOCAL against extracted PDF text | 269 |
| Newly UNVERIFIABLE: quote's numbers absent (ICI) | 1 |
| Newly UNVERIFIABLE: `pdf_not_extracted` (FDA) | 2 |

The PDF-only pass exposed the concrete class named in the fix prompt. A full cached-corpus
pass was then required because numeric mismatch is source-format agnostic: HTML and SEC
filings can also share vocabulary while disagreeing on the quote's numbers. That pass
surfaced 62 `quote_not_found` claims (58 had previously cleared the 0.60 overlap) plus the
two `pdf_not_extracted` claims.

Post-application corpus tally:

| verify_status | Claims |
|---|---:|
| VERIFIED_LOCAL | 5,169 |
| SELF_ATTESTED | 58 |
| UNVERIFIABLE | 64 |

The corrected checked denominator is 5,233 and the corpus unverifiable rate is
**64/5,233 = 1.22%**. The previous 0.077% remains in dated results as the number reported
then, with this correction linked beside it.

Concrete correction: `c_520000000002` remains unchanged as a historical claim, but its
status is now `UNVERIFIABLE` (`quote_not_found`). The cached ICI PDF extracts normally;
the defect was not that the cache stored original PDF bytes. The extracted page describes
different values and a different period, while the old whole-page vocabulary overlap
still reached 0.8182. The claim is not rewritten to the page's figures because that would
be new research rather than verification.

No verdict changes. All affected research remains SHADOW.
