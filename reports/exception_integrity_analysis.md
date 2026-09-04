# Exception Integrity & Sample-Induced Bias Analysis

**Project:** AWM ControlWatch — Phase 3 Hardening  
**Date:** 2026-09-04  
**Subject:** Scientific Root-Cause Investigation of Phase 2 Sample Artifacts (9,542 Exceptions) vs. Full-Quarter Production Population (7,393 Exceptions)

---

## 1. Executive Summary

In Phase 2 validation, initial execution against SEC Form N-PORT Q3 2025 data generated **9,542 exceptions**, with Reconciliation Control `REC-002` alone reporting **6,596 critical exceptions** and a pass rate of **0.06%**.

An analytical audit revealed that **99.2% of the REC-002 exceptions in Phase 2 were sample-induced statistical artifacts** caused by truncating the ingestion pipeline with `--sample 5000` holdings. While 6,600 registered funds were ingested into the database, only 53 funds received any holdings in the 5,000-row sample. Consequently, 6,547 funds appeared to have $0.00 in portfolio holdings against billions in reported assets, triggering artificial 100% variance alarms.

In Phase 3, the platform was hardened:
1. **Full-Quarter Population Ingestion:** Ingested all **6,025,567 holdings** from the official SEC archive, achieving **99.95% fund coverage** (6,597 of 6,600 funds).
2. **Defensible Control Semantics:** Refactored `REC-002` to distinguish between funds with materially inconsistent holdings vs. funds where Part C filing schedules were omitted (`DATA_AVAILABILITY`).
3. **Rigorous Taxonomy:** Separated findings into `ANALYTICAL_EXCEPTION` (3,295), `DATA_QUALITY_EXCEPTION` (1,540), and `DATA_AVAILABILITY` (2,558).
4. **Risk Engine Integrity:** Assigned `risk_level = INSUFFICIENT_EVIDENCE` to data-unavailable items, ensuring they never distort operational risk breach rates.

---

## 2. Quantitative Comparison: Phase 2 vs. Phase 3

| Dimension | Phase 2 (Sample Pipeline) | Phase 3 (Full Population Hardened) | Variance / Resolution |
|:---|:---:|:---:|:---|
| **Holdings Ingested** | 5,000 holdings | **6,025,567 holdings** | Full official SEC population loaded (+120,411%) |
| **Period 2025-06-30 Holdings** | 5,000 holdings | **2,291,229 holdings** | Full quarterly reporting population |
| **Fund Coverage Ratio** | 0.80% (53 / 6,600 funds) | **99.95% (6,597 / 6,600 funds)** | +99.15% absolute coverage increase |
| **Funds Without Holdings** | 6,547 funds | **3 funds** (Part C schedule omitted in SEC filing) | 6,544 false missing funds eliminated |
| **REC-002 Exceptions** | 6,596 exceptions | **640 exceptions** (637 analytical + 3 data unavailable) | **90.3% reduction in false alarms** |
| **REC-002 Pass Rate** | 0.06% | **90.34%** | Defensible operational pass rate |
| **KRI-002 (Recon Rate)** | 99.9% (`RED`) | **9.70% (`AMBER`)** | Denominator properly excludes unavailable data |
| **KCI-001 (Control Execution)** | 100.0% | **100.0%** | Full automation across all 16 controls |
| **Automated Test Suite** | 92 tests passing | **96 tests passing (100%)** | Zero regressions + semantic availability tests |

---

## 3. Root-Cause Decomposition of Phase 2 Exceptions

### 3.1 The Truncation Artifact in `REC-002`
In Phase 2, `REC-002` calculated:
$$\text{diff\_pct} = \frac{|\sum \text{holdings.value} - \text{funds.total\_assets}|}{\text{funds.total\_assets}} \times 100$$

Because the sample parser halted after 5,000 holding rows, only the first 53 funds in the TSV file had records in the `holdings` table:
- **Funds 1 to 53:** Evaluated normally.
- **Funds 54 to 6,600 (6,547 funds):** Database query returned `COALESCE(SUM(h.value), 0) = 0.00`.
- Result: $\text{diff\_pct} = \frac{|0 - \text{total\_assets}|}{\text{total\_assets}} \times 100 = 100.0\%$.
- Every single one of these 6,547 funds was flagged as a `CRITICAL` portfolio completeness failure.

### 3.2 Full-Population Reality
When all 2,291,229 holdings for the period were loaded:
- **5,591 funds (84.7%)** matched reported total assets within **5% variance**.
- **5,960 funds (90.3%)** matched within **10% variance**.
- **637 funds (9.7%)** had variances exceeding 10%. Detailed analysis indicates these are genuine structural differences inherent in mutual fund accounting:
  1. *Gross vs. Net Assets:* SEC N-PORT Part B Item B.1 reports gross assets (including receivables, collateral, and cash equivalents), while Part C itemizes investment securities.
  2. *Derivatives & Notional Values:* Swaps and forward contracts report unrealized gain/loss in Part C rather than notional exposure.
  3. *Leverage & Borrowing:* Closed-end funds with debt leverage exhibit structural discrepancies between gross asset base and security schedule totals.
- **3 funds (0.05%)** had 0 holdings because the registrants legitimately omitted Part C (e.g., non-portfolio trusts or liquidated funds during the period).

---

## 4. Taxonomy Hardening & Operational Integrity

To eliminate data-availability bias in production risk metrics, the platform implemented a 4-tier exception taxonomy:

| Taxonomy Category | Definition | Example Finding | Operational Handling | Risk Scoring |
|:---|:---|:---|:---|:---|
| `ANALYTICAL_EXCEPTION` | Genuine portfolio metric variance against benchmark policy thresholds. | `CONC-001` top-10 concentration >45%; `REC-002` gross asset variance >10%. | Assigned to desk; remediation tracked with MTTR SLA. | Deterministic scoring ($1 \dots 125$) |
| `DATA_QUALITY_EXCEPTION` | Missing identifiers, duplicate lines, or invalid arithmetic in filing. | `DQ-001` NULL security identifier; `DQ-003` negative share balance. | Logged for vendor data feed triage and reference data scrubbing. | Scored based on data impact |
| `DATA_AVAILABILITY` | Evidence not reported in filing or prior period filing absent. | `REC-002` Part C omitted (3 funds); `RPT-002` missing quarterly period. | Logged as filing documentation gap; not penalized as risk breach. | `INSUFFICIENT_EVIDENCE` (Score = 0) |
| `CONTROL_FAILURE` | System execution fault (database error, pipeline timeout). | Unhandled schema exception during parsing. | IT incident ticket generated; execution marked `FAILED`. | N/A (Technical Alert) |

---

## 5. Risk Engine & AI Refusal Policy

1. **Deterministic Authority:**
   The AI copilot and LLM prompts are strictly prohibited from determining authoritative risk scores. The mathematical engine remains the sole source of truth.
2. **Missing-Evidence Refusal:**
   When queries involve funds or controls with `DATA_AVAILABILITY` or incomplete evidence, the AI copilot must refuse speculation and output:
   > *"There is insufficient evidence in the reported filings to determine whether this represents a genuine control breach."*
3. **Auditability:**
   Every AI analysis generates an immutable `ai_analysis` record with SHA-256 evidence hash, validation issue list, and prompt-injection check results.

---

## 6. Conclusion & Recommendation

The transition from Phase 2 sample validation to Phase 3 full-quarter population validation has transformed AWM ControlWatch from a conceptual prototype into a mathematically and operationally defensible platform. The analytical outputs accurately reflect the empirical realities of SEC Form N-PORT filings.
