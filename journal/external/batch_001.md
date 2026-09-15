# External review batch 001

10 companies our local model could not read. Paste everything below the line into Gemini, then save its JSON reply as
`journal/external/batch_001_reply.json` and run:

    .venv\Scripts\python.exe -m clab.runner.ingest_external --file journal/external/batch_001_reply.json

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
  CSL - Carlisle Companies
    CIK 0000790051 | Industrials / Industrial Conglomerates
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  MPT - Medical Properties Trust
    CIK 0001287865 | Real Estate / Health Care REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  PK - Park Hotels & Resorts
    CIK 0001617406 | Real Estate / Hotel & Resort REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  FCPT - Four Corners Property Trust, Inc.
    CIK 0001650132 | Real Estate / Other Specialized REITs
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  MFP - Midera Food Processing, Inc.
    CIK 0002088281 | Industrials / Industrial Machinery & Supplies & Components
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - regulatory_barriers: Regulatory barriers
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  PWR - Quanta Services
    CIK 0001050915 | Industrials / Construction & Engineering
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  TPL - Texas Pacific Land Corporation
    CIK 0001811074 | Energy / Oil & Gas Exploration & Production
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  HASI - Hannon Armstrong Sustainable Infrastructure Capital, Inc.
    CIK 0001561894 | Financials / Specialized Finance
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  NJR - New Jersey Resources
    CIK 0000356309 | Utilities / Gas Utilities
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages

  AMRX - Amneal Pharmaceuticals, Inc.
    CIK 0001723128 | Health Care / Pharmaceuticals
    score these dimensions:
      - technological_advantage: Technological advantage
      - economies_of_scale: Economies of scale
      - switching_costs: Switching costs
      - network_effects: Network effects
      - intellectual_property: Intellectual property
      - brand: Brand
      - manufacturing_complexity: Manufacturing complexity
      - distribution: Distribution
      - customer_relationships: Customer relationships
      - data_advantages: Data advantages
