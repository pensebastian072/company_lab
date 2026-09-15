# External review batch 006

10 companies our local model could not read. Paste everything below the line into Gemini, then save its JSON reply as
`journal/external/batch_006_reply.json` and run:

    .venv\Scripts\python.exe -m clab.runner.ingest_external --file journal/external/batch_006_reply.json

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
  NHI - National Health Investors, Inc.
    CIK 0000877860 | Real Estate / Health Care REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  NXRT - NexPoint Residential Trust, Inc.
    CIK 0001620393 | Real Estate / Diversified REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  HCC - Warrior Met Coal, Inc.
    CIK 0001691303 | Materials / Steel
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  HTH - Hilltop Holdings Inc.
    CIK 0001265131 | Financials / Regional Banks
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  AMR - Alpha Metallurgical Resources, Inc.
    CIK 0001704715 | Materials / Steel
    score these dimensions:
      - economies_of_scale: Economies of scale
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  NLY - Annaly Capital Management
    CIK 0001043219 | Financials / Mortgage REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  VGNT - Versigent PLC
    CIK 0002078008 | Consumer Discretionary / Other Specialty Retail
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  ADIG - ADI Global Distribution
    CIK 0002105139 | Information Technology / Electronic Equipment & Instruments
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  IESC - IES Holdings
    CIK 0001048268 | Industrials / Construction & Engineering
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  FIX - Comfort Systems USA
    CIK 0001035983 | Industrials / Construction & Engineering
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - data_advantages: Data advantages
