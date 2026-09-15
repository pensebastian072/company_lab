# External review batch 010

10 companies our local model could not read. Paste everything below the line into Gemini, then save its JSON reply as
`journal/external/batch_010_reply.json` and run:

    .venv\Scripts\python.exe -m clab.runner.ingest_external --file journal/external/batch_010_reply.json

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
  PLMR - Palomar Holdings, Inc.
    CIK 0001761312 | Financials / Property & Casualty Insurance
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  STC - Stewart Information Services Corporation
    CIK 0000094344 | Financials / Property & Casualty Insurance
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  VICI - Vici Properties
    CIK 0001705696 | Real Estate / Hotel & Resort REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  MSEX - MIDDLESEX WATER CO
    CIK 0000066004 | Utilities / Water Supply
    score these dimensions:
      - economies_of_scale: Economies of scale
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  MUR - Murphy Oil
    CIK 0000717423 | Energy / Oil & Gas Exploration & Production
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  BYD - Boyd Gaming
    CIK 0000906553 | Consumer Discretionary / Casinos & Gaming
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  HTO - H2O America
    CIK 0000766829 | Utilities / Water Utilities
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  APLE - Apple Hospitality REIT, Inc.
    CIK 0001418121 | Real Estate / Hotel & Resort REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  SAFE - Safehold Inc.
    CIK 0001095651 | Real Estate / Diversified REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages

  EPR - EPR Properties
    CIK 0001045450 | Real Estate / Other Specialized REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - data_advantages: Data advantages
