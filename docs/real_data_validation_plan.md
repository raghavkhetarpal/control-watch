# AWM ControlWatch — Real SEC N-PORT Data Validation Plan

> **Phase 2:** End-to-End Validation and Verification against Official SEC Form N-PORT Public Datasets.

---

## 1. Current Architecture

AWM ControlWatch is structured as an institutional-grade educational and analytical monitoring platform:

```
SEC Form N-PORT Quarterly Dataset (ZIP / TSVs)
                 │
                 ▼
     [SEC N-PORT Downloader]  <── Checksum & Retry Logic
                 │
                 ▼
     [SEC N-PORT Parser]      <── Chunked extraction (Pandas stream)
                 │
                 ▼
       [Data Normalizer]      <── Identifier, date, categorical clean
                 │
                 ▼
    [PostgreSQL Database]     <── 18 Relational tables with FK integrity
         │            │
         │            ▼
         │    [16 Deterministic Controls] (DQ, Recon, Val, Conc, Liq, Rpt, Cls)
         │            │
         │            ▼
         │    [Risk Scoring Engine]   <── Inherent vs. Residual Risk
         │            │
         │            ▼
         │    [KRI / KCI / KPI Engine]<── RAG status & trends
         │            │
         │            ▼
         │    [Exception Manager]     <── 8-stage lifecycle & remediation
         │            │
         │            ▼
         │    [Append-Only Audit Trail]
         ▼            ▼
     [FastAPI REST API]  <───>  [Evidence-Grounded AI Analyst]
                 │
                 ▼
    [Streamlit Dashboard (8 Pages)]
```

---

## 2. Validation Objectives

1. **End-to-End Execution:** Prove that raw, unmodified SEC Form N-PORT data flows seamlessly from official SEC servers into PostgreSQL, passes through all 16 analytical controls, calculates risk indicators, generates exceptions, and feeds the API, dashboard, and AI copilot.
2. **Deterministic Integrity:** Ensure no financial or operational claims are fabricated. Every metric, risk score, and exception must be directly traceable to underlying SEC source filings.
3. **Idempotency & Resilience:** Verify that downloading, extracting, parsing, and ingesting chunks is idempotent, memory-safe, and gracefully handles network hiccups and duplicate filings.
4. **Investigation Workflow Validation:** Verify that a real analytical exception can be triaged, assigned, remediated, validated, and closed with complete append-only audit trail logging.
5. **AI Evidence Grounding & Injection Defense:** Confirm that the GenAI copilot operates strictly from structured evidence and repels prompt-injection attacks embedded within public filing data.

---

## 3. SEC Data Source

- **Source:** SEC Division of Economic and Risk Analysis (DERA)
- **Official URL:** `https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets`
- **Archive Pattern:** `https://www.sec.gov/files/dera/data/form-n-port-data-sets/{year}q{quarter}_nport.zip`
- **Selected Initial Quarter:** `2025q3` (recent confirmed filing quarter)
- **Secondary Quarter (Reconciliation):** `2025q2` (for period-over-period `T` vs `T-1` verification)
- **Primary TSV Files:**
  - `SUBMISSION.tsv`: Submission metadata, accession number, filing date, report period.
  - `REGISTRANT.tsv`: Fund family / sponsor CIK, registrant name, LEI.
  - `SERIES.tsv`: Fund series identifiers and names.
  - `FUND_REPORTED_INFO.tsv`: Fund-level net assets, total assets, liabilities.
  - `FUND_REPORTED_HOLDING.tsv`: Granular position-level holdings, CUSIP, ISIN, balance, value, %, asset category.

---

## 4. Expected Ingestion Stages

1. **Downloader Stage:**
   - Fetch remote archive using `httpx` with SEC-compliant User-Agent.
   - Verify HTTP status, handle retries with exponential backoff.
   - Compute SHA-256 checksum and verify archive integrity.
   - Cache locally in `data/`; skip duplicate downloads when local size and hash match.
2. **Extraction & Inspection Stage:**
   - Inspect archive contents without full unzipping to memory.
   - Map real TSV column headers against PostgreSQL schema (`docs/sec_nport_column_mapping.csv`).
3. **Normalization & Pre-Load Validation Stage:**
   - Normalize string encodings (UTF-8 with Latin-1 fallback).
   - Format dates (`YYYY-MM-DD`), numeric scales, uppercase CUSIP (9 char) and ISIN (12 char).
   - Clean category codes (`EC`, `DBT`, `USG`, `CORP`).
   - Validate pre-load row integrity.
4. **Relational Loading Stage (Referential Hierarchy):**
   - Stage 1: `ingestion_runs` (run tracking).
   - Stage 2: `submissions` (accession numbers).
   - Stage 3: `registrants` (CIKs).
   - Stage 4: `fund_series` (series linked to CIK).
   - Stage 5: `funds` (linked to submissions & series).
   - Stage 6: `holdings` (linked to funds & submissions).
   - Stage 7: `reporting_periods` (summary rollup).
   - Stage 8: `data_quality_results` (ingestion DQ metrics).

---

## 5. Validation Checkpoints

| Checkpoint | Validation Task | Success Metric |
|---|---|---|
| **CP-1: Downloader** | Download selected quarter | SHA-256 hash matches, file cached, zero corruptions |
| **CP-2: TSV Header Audit** | Compare raw TSV columns to DB | Documented column mapping for 100% of required fields |
| **CP-3: Pipeline Ingestion** | Run chunked load into PostgreSQL | Zero memory spikes, zero FK violations, idempotency confirmed |
| **CP-4: DB Integrity Audit** | Run `scripts/validate_real_data.py` | Valid record counts, zero orphan records, clean distributions |
| **CP-5: Control Execution** | Execute all 16 controls | 16/16 controls executed, runtime and exceptions logged |
| **CP-6: False-Positive Review** | Review sample exceptions | Exceptions categorized (Valid, False Positive, Data Limit) |
| **CP-7: Period Reconciliation** | Run `REC-001` & `REC-002` across periods | Distinguishes new, removed, and shifted positions accurately |
| **CP-8: Metric Generation** | Compute 7 KRIs, 7 KCIs, 8 KPIs | Deterministic RAG ratings, division-by-zero handled |
| **CP-9: Exception Workflow** | Complete lifecycle for real exception | Full state machine progression + audit events logged |
| **CP-10: Audit Trail** | Verify immutability of audit log | Append-only integrity verified by automated tests |
| **CP-11: API Verification** | Query FastAPI endpoints | HTTP 200 on all core endpoints with valid Pydantic schemas |
| **CP-12: Dashboard Verification**| Render 8 Streamlit pages | All 8 pages load with live real-data visualizations |
| **CP-13: AI Copilot Testing** | Grounding & prompt-injection tests | Responses cite real data, 100% injection defense pass |
| **CP-14: Test Suite & CI** | Run pytest with coverage | \(\ge 92\) tests pass, coverage preserved or improved |

---

## 6. Known Limitations

1. **Reporting Latency:** SEC Form N-PORT filings are published quarterly on a 60-day lag. They reflect historical position dates, not real-time intraday positions.
2. **Analytical Proxies:** Public SEC filings do not include institutional operational loss logs or internal trade confirmation feeds. Controls are analytical monitoring indicators rather than proprietary operational measures.
3. **Market Liquidity Proxy:** Trading volume data is not present in Form N-PORT; liquidity risk is evaluated via asset classification proxies rather than actual order-book depth.
4. **Illustrative Thresholds:** All numerical thresholds (e.g. \(35\%\) concentration, \(60\) days reporting delay) are illustrative analytical thresholds for educational demonstration.

---

## 7. Acceptance Criteria

- [ ] Downloader successfully retrieves official SEC N-PORT archive with verifiable SHA-256 hash.
- [ ] Pipeline normalizes and loads real SEC filings into PostgreSQL with zero referential integrity violations.
- [ ] Second identical run produces zero duplicate records (idempotent).
- [ ] All 16 controls execute against real data and generate explainable analytical exceptions.
- [ ] Period-over-period reconciliation (`REC-001`, `REC-002`) accurately detects holdings changes.
- [ ] 7 KRIs, 7 KCIs, and 8 KPIs are calculated with deterministic RAG ratings.
- [ ] Complete exception lifecycle (`DETECTED` \(\rightarrow\) `CLOSED`) is demonstrated with full audit trail logging.
- [ ] FastAPI and Streamlit dashboard operate smoothly against the populated database.
- [ ] AI Copilot answers analytical queries strictly grounded in database evidence without hallucinations or vulnerability to prompt injection.
- [ ] Pytest suite achieves 100% pass rate with \(\ge 92\) automated tests.
- [ ] Comprehensive validation report (`reports/FINAL_VALIDATION_REPORT.md`) is delivered.
