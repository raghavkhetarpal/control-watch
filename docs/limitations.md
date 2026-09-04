# Limitations and Disclaimers

**CRITICAL DISCLAIMER: This project is an educational/research implementation. It does not replicate, represent, or utilize Goldman Sachs proprietary systems, controls, internal data, or risk frameworks.**

## Public Data Limitations
- **Frequency**: SEC Form N-PORT data is filed quarterly (though reported monthly). It is not real-time.
- **Latency**: Data is typically publicly released 60 days after the end of the reporting period. Therefore, any analysis reflects historical state, not current market exposure.
- **Data Quality**: SEC filings are self-reported by registrants and may contain errors, typos, or omissions. The ControlWatch system detects these but cannot correct the upstream source data.

## Analytical Control Limitations
- **Derived Controls**: The controls implemented here are analytical heuristics based on public data fields. They are not statutory regulatory requirements unless explicitly mapped to a specific SEC rule.
- **Concentration Thresholds**: All thresholds (e.g., 5% issuer limit) are **illustrative analytical thresholds** used to demonstrate system functionality. They do not represent regulatory mandates or institutional internal limits.
- **Liquidity**: Liquidity metrics are proxy-based (relying on reporting classifications) rather than calculated from actual market trading volume or institutional liquidity models.

## Proprietary Systems & Equivalence
- **No Proprietary Data**: This system has no access to actual trade flows, Order Management Systems (OMS), accounting platforms, or internal institutional risk engines.
- **Market Data**: There is no live price feed. Valuation controls operate solely on the periodic values reported in the N-PORT dataset.
- **Non-Equivalence**: The architecture, taxonomy, and methodology are generalized software engineering patterns and do not reflect the architecture of institutional systems.

## AI Copilot Limitations
- **Supplementary Analysis**: The LLM-based AI Copilot provides supplementary insights based strictly on the data presented to it. It is not authoritative.
- **Hallucination Risk**: While prompt engineering constraints are in place, the AI may misinterpret data trends. All AI output should be independently verified by an analyst.
