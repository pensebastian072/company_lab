"""External & sector intelligence - the third source of truth (V3).

The measured half asks "what do the numbers show?". The judged half asks "what does
the company say about itself?". This package asks the question neither can answer:
"what is actually happening around this company?"

The governing rule, and the reason this is not just another component:

    External research changes what we BELIEVE about SG and BQ, and how CONFIDENT we
    are, and whether a company clears a GATE. It does not add points to the 94.

Nothing here scores a company on its own. Codex returns closed-vocabulary categoricals
and cited claims; every number is computed locally, by `score.py` from the categoricals
and by `verify.py` from the citations. `finalize.py` is the gate, not the agent - the
same invariant the options desk runs on ("Codex does not apply the gates - the
finalizer does").
"""
