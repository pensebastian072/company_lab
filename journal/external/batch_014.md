# External review batch 014

10 companies our local model could not read. Paste everything below the line into Gemini, then save its JSON reply as
`journal/external/batch_014_reply.json` and run:

    .venv\Scripts\python.exe -m clab.runner.ingest_external --file journal/external/batch_014_reply.json

Every quote is checked against the filing text on disk before it can touch a score.

---

You are scoring the competitive moat of 10 US-listed companies from their
most recent SEC 10-K annual report.

For EACH company below, score ONLY the dimensions listed for it. Rules, all of which
matter more than completeness:

1. Every score is an INTEGER from 0 to 5. 0 = a commodity business that a well-funded
   competitor could replicate; 5 = displacing it would be exceptionally difficult.
2. "evidence" MUST be a VERBATIM quote copied from that company's own 10-K - not from a
   press release, not from your general knowledge, not paraphrased. Copy the words
   exactly, 10-40 words.
3. If the 10-K does not support a dimension, return "score": null. A null is a correct
   answer. An invented quote is not, and every quote is checked against the filing text
   before the score is used - a quote that is not found there is DISCARDED along with its
   score.
4. If a dimension does not apply to the business at all - manufacturing complexity for a
   REIT, network effects for a utility - return "score": null and set
   "not_applicable": true. That is different from "the filing does not say".
5. "rationale" is one sentence in your own words, under 200 characters.

Respond with ONE JSON object and nothing else. No markdown fences, no commentary:

{"companies": [
  {"ticker": "XYZ",
    "dimensions": {
      "economies_of_scale": {"score": 3, "not_applicable": false,
        "rationale": "...", "evidence": "verbatim quote from the 10-K"}
    }
  }
]}

THE COMPANIES
  SLG - SL Green Realty
    CIK 0001040971 | Real Estate / Office REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  CHCO - City Holding Company
    CIK 0000726854 | Financials / Regional Banks
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  EQH - Equitable Holdings
    CIK 0001333986 | Financials / Diversified Financial Services
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  KRMN - Karman Holdings
    CIK 0002040127 | Industrials / Aerospace & Defense
    score these dimensions:
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  PSKY - Paramount Skydance Corporation
    CIK 0002041610 | Communication Services / Movies & Entertainment
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  JBGS - JBG SMITH Properties
    CIK 0001689796 | Real Estate / Diversified REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  GBCI - Glacier Bancorp
    CIK 0000868671 | Financials / Regional Banks
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  VNO - Vornado Realty Trust
    CIK 0000899689 | Real Estate / Office REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  MTH - Meritage Homes Corporation
    CIK 0000833079 | Consumer Discretionary / Homebuilding
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  WAL - Western Alliance Bancorporation
    CIK 0001212545 | Financials / Regional Banks
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages
