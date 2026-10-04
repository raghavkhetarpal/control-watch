# AWM ControlWatch — Comprehensive System & Engineering Documentation

**Investment Operations Risk & Control Monitoring Platform**  
*Educational & Research Implementation based on publicly available SEC Form N-PORT data.*

---

> [!IMPORTANT]
> **DISCLAIMER & INSTITUTIONAL BOUNDARY NOTICE**  
> This platform is an educational and research implementation designed to demonstrate core concepts relevant to an Asset & Wealth Management (AWM) Monitoring & Testing function.  
> **It does NOT replicate, represent, or claim to reproduce Goldman Sachs' (or any other financial institution's) internal proprietary systems, controls, data, models, or operational risk frameworks.** All data utilized originates from public SEC EDGAR / DERA Form N-PORT bulk datasets. All risk scoring algorithms, control thresholds, liquidity proxies, and remediation workflows are illustrative, educational engineering implementations.

---

## Table of Contents

1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [Objectives, Scope & Key Capabilities](#2-objectives-scope--key-capabilities)
3. [System Architecture & Data Topology](#3-system-architecture--data-topology)
4. [Relational Database Schema & Data Dictionary](#4-relational-database-schema--data-dictionary)
5. [Data Ingestion & Normalization Pipeline](#5-data-ingestion--normalization-pipeline)
6. [Deterministic Control Framework (16 Controls)](#6-deterministic-control-framework-16-controls)
7. [Exception Integrity & 4-Tier Taxonomy](#7-exception-integrity--4-tier-taxonomy)
8. [Risk Scoring & Residual Risk Modeling](#8-risk-scoring--residual-risk-modeling)
9. [Metrics Engine (KRIs, KCIs, and KPIs)](#9-metrics-engine-kris-kcis-and-kpis)
10. [Exception Lifecycle & Remediation Workflow](#10-exception-lifecycle--remediation-workflow)
11. [AI Analyst Copilot & Safety Guardrails](#11-ai-analyst-copilot--safety-guardrails)
12. [User Interface & Streamlit Dashboard](#12-user-interface--streamlit-dashboard)
13. [FastAPI REST Interface](#13-fastapi-rest-interface)
14. [Technology Stack & Dependency Inventory](#14-technology-stack--dependency-inventory)
15. [Installation, Configuration & Deployment](#15-installation-configuration--deployment)
16. [Verification, Quality Assurance & Test Suite](#16-verification-quality-assurance--test-suite)
17. [Engineering Design Rationale](#17-engineering-design-rationale)
18. [Assumptions, Known Limitations & Future Considerations](#18-assumptions-known-limitations--future-considerations)
19. [Operational Runbook & Troubleshooting](#19-operational-runbook--troubleshooting)

---

## 1. Executive Summary & Problem Statement

### 1.1 The Operational Risk Problem in Asset & Wealth Management
In modern Asset & Wealth Management (AWM) operations, fund managers, depositaries, and compliance teams oversee thousands of investment portfolios holding millions of security positions across global markets. Monitoring and testing functions face critical operational challenges:
- **Data Volume and Heterogeneity:** Portfolio schedules contain millions of complex instruments (equities, debt, asset-backed securities, short-term cash vehicles, derivatives) reported across inconsistent filing timelines.
- **Data Quality & Completeness Breaks:** Missing security identifiers (CUSIP, ISIN, LEI), invalid negative balances, impossible coupon rates, and misclassified assets degrade post-trade accounting and regulatory compliance.
- **Reconciliation Discrepancies:** Variations between gross reported fund assets and granular security schedules arise from derivatives accounting (unrealized gain/loss vs. notional exposure), cash payables/receivables, and leverage facilities.
- **Concentration & Liquidity Exposure:** Breaches of concentration limits (single positions, single issuers, illiquid asset categories) must be detected promptly to manage liquidity and regulatory risk.
- **Operational Sprawl & Remediation Tracking:** When exceptions occur, organizations require an auditable lifecycle—from automated detection and severity triage through root cause analysis, action assignment, validation, and immutable audit logging.
- **AI Hallucination Risk:** Generative AI tools applied to financial operations often invent facts or misinterpret missing data as fraud or regulatory breaches.

### 1.2 What AWM ControlWatch Does
**AWM ControlWatch** is an end-to-end, production-quality, educational/research software platform built to solve these challenges using actual public regulatory filings. The system:
1. Ingests and normalizes multi-gigabyte SEC Form N-PORT bulk datasets containing 6,000,000+ security positions.
2. Executes 16 automated, deterministic controls across 7 risk categories in under 15 seconds.
3. Implements a scientific 4-tier exception taxonomy that distinguishes real analytical anomalies from data-availability gaps and reporting omissions.
4. Calculates deterministic inherent and residual risk scores using mathematical formulas.
5. Computes and snapshots 7 Key Risk Indicators (KRIs), 7 Key Control Indicators (KCIs), and 8 operational KPIs.
6. Manages an 8-stage exception remediation lifecycle backed by an append-only audit trail.
7. Delivers an evidence-grounded AI Analyst Copilot with prompt-injection defense and mandatory missing-evidence refusal.
8. Provides a unified 8-page interactive Streamlit dashboard and a RESTful FastAPI backend.

---

## 2. Objectives, Scope & Key Capabilities

### 2.1 Project Objectives
- **Demonstrate Institutional-Grade Testing:** Provide a fully functional reference implementation of an AWM Monitoring & Testing function.
- **Handle Real-World Scale:** Seamlessly process full quarterly SEC datasets (millions of records) with bounded memory consumption and fast execution times.
- **Maintain Deterministic Authority:** Retain strict mathematical formulas for risk scoring, preventing AI models from hallucinating or overriding authoritative risk assessments.
- **Enforce Auditability:** Ensure every state transition, exception assignment, and remediation action produces an immutable audit record with before/after state diffs.
- **Deliver Scientific Integrity:** Differentiate genuine investment breaks from reporting schedule artifacts and baseline gaps.

### 2.2 System Scope
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             IN-SCOPE CAPABILITIES                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Public SEC Form N-PORT Q3 2025 dataset ingestion & verification           │
│  • High-throughput PostgreSQL binary COPY streaming (34k+ rows/sec)         │
│  • 16 deterministic controls across 7 operational risk domains              │
│  • Inherent & residual risk scoring formulas                                │
│  • Automated KRI/KCI/KPI calculation engine with RAG status & trends        │
│  • 8-stage exception management state machine                               │
│  • Root cause classification & remediation action item tracking             │
│  • Append-only audit trail table (audit_events)                             │
│  • FastAPI backend (15+ endpoints, OpenAPI documentation, timing headers)   │
│  • Streamlit interactive UI (8 dedicated functional pages)                  │
│  • AI Copilot with multi-provider abstraction & 5+ injection defenses       │
│  • 96 automated tests with 100% pass rate                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Out-of-Scope & Non-Equivalence Boundaries
- **Proprietary Systems:** Does NOT reproduce Goldman Sachs' proprietary Order Management Systems (OMS), internal risk engines (e.g., SecDB), or internal compliance procedures.
- **Real-Time Intraday Feeds:** SEC Form N-PORT is filed 30 to 60 days after month/quarter end; the platform operates on regulatory batch reporting rather than sub-second trade execution feeds.
- **Legal/Regulatory Enforcement:** Exceptions flagged by the platform are illustrative analytical anomalies; they do not represent formal regulatory violations or findings of fraud.

---

## 3. System Architecture & Data Topology

### 3.1 High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph S1["1. External Regulatory Data Source"]
        SEC["SEC EDGAR / DERA Bulk Repository\n(2025q3_nport.zip — 468.9 MB)"]
    end

    subgraph S2["2. Ingestion & Transformation Engine"]
        DL["sec_nport_downloader.py\n(HTTPX + Tenacity Retries + SHA-256)"]
        PARSE["sec_nport_parser.py / ingest_full.py\n(Chunked Streaming TSV Reader)"]
        NORM["normalizer.py\n(CUSIP/ISIN/LEI Normalization, Date Parsing)"]
        VAL["validators.py\n(Pre/Post Ingestion Referential Integrity)"]
    end

    subgraph S3["3. PostgreSQL 16 Relational Engine"]
        DB_SUB[("submissions\nregistrants\nfund_series\nfunds")]
        DB_HLD[("holdings\n(6,025,567 rows)")]
        DB_CTL[("control_definitions\ncontrol_executions\ncontrol_exceptions")]
        DB_MET[("kri_snapshots\nkci_snapshots\nkpi_snapshots\nrisk_assessments")]
        DB_REM[("remediation_items\naudit_events\nai_analysis")]
    end

    subgraph S4["4. Analytical & Business Logic Engines"]
        CTL_ENG["Control Engine (16 Controls)\n(DQ, REC, VAL, CONC, LIQ, RPT, CLS)"]
        RISK_ENG["Risk Scoring Engine\n(Impact × Likelihood × [6 - Effectiveness])"]
        MET_ENG["Metrics Engine\n(7 KRIs, 7 KCIs, 8 KPIs)"]
        EXC_MGR["Exception & Remediation Manager\n(8-State Lifecycle + Audit Logger)"]
    end

    subgraph S5["5. Intelligence & Service Layer"]
        API["FastAPI REST Application\n(Port 8000 — 15+ Endpoints)"]
        AI_COP["AI Analyst Copilot\n(Evidence Grounding + Injection Defense)"]
    end

    subgraph S6["6. Presentation & Analysis"]
        UI["Streamlit Interactive Dashboard\n(Port 8501 — 8 Pages)"]
        ANALYST(("Risk / Control Analyst"))
    end

    SEC -->|Download ZIP| DL
    DL -->|Extract & Stream| PARSE
    PARSE -->|Clean Data| NORM
    NORM -->|Validate Schema| VAL
    VAL -->|High-Speed COPY| DB_SUB
    VAL -->|High-Speed COPY| DB_HLD

    DB_HLD & DB_SUB -->|Query Records| CTL_ENG
    CTL_ENG -->|Exceptions| RISK_ENG
    RISK_ENG -->|Scored Exceptions| DB_CTL
    DB_CTL -->|Aggregate Metrics| MET_ENG
    MET_ENG -->|Snapshots| DB_MET
    DB_CTL -->|Manage Life Cycle| EXC_MGR
    EXC_MGR -->|Log Transitions| DB_REM

    DB_SUB & DB_HLD & DB_CTL & DB_MET & DB_REM -->|SQLAlchemy| API
    DB_CTL & DB_HLD -->|Structured Context| AI_COP
    AI_COP -->|Validated Explanations| API

    API -->|REST / Direct Connect| UI
    UI <-->|Triage & Investigate| ANALYST
```

### 3.2 Data Flow Progression

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Risk Analyst
    participant UI as Streamlit UI
    participant API as FastAPI Backend
    participant Engine as Control & Risk Engine
    participant DB as PostgreSQL Database
    participant Copilot as AI Copilot

    Analyst->>UI: Select Reporting Period (e.g., 2025-06-30)
    UI->>API: GET /metrics/kris?period=2025-06-30
    API->>DB: Query kri_snapshots & control_executions
    DB-->>API: Return KRI values, status (RAG), and trends
    API-->>UI: Display Executive Overview Cards

    Analyst->>UI: Drill into KRI-002 (Reconciliation Exception Rate)
    UI->>API: GET /exceptions?control_id=REC-002&status=DETECTED
    API->>DB: Query control_exceptions with joined funds
    DB-->>API: Return list of 640 exceptions with evidence JSON
    API-->>UI: Render interactive filterable data table

    Analyst->>UI: Click "Ask AI to Explain Exception #9545"
    UI->>Copilot: POST /ai/analyze (exception_id=9545)
    Copilot->>DB: Fetch structured evidence (holdings, fund total assets, delta)
    DB-->>Copilot: Return evidence dict
    Copilot->>Copilot: Hash evidence & validate prompt injection
    Copilot->>Copilot: Check data availability (refuse if insufficient)
    Copilot-->>UI: Return grounded narrative + Validation Badge (VALIDATED)

    Analyst->>UI: Transition Exception: DETECTED -> ASSIGNED -> REMEDIATION_PLANNED
    UI->>API: POST /exceptions/9545/remediation (owner, due_date, action)
    API->>DB: Insert remediation_items & INSERT audit_events (diff log)
    DB-->>API: Commit transaction
    API-->>UI: Update status badge and audit trail view
```

---

## 4. Relational Database Schema & Data Dictionary

The PostgreSQL database schema consists of **20 active relational tables** specifically optimized for investment operations, high-performance indexing, audit logging, and metric historical snapshots.

```mermaid
erDiagram
    ingestion_runs ||--o{ submissions : triggers
    submissions ||--o{ funds : contains
    registrants ||--o{ fund_series : registers
    registrants ||--o{ funds : sponsors
    fund_series ||--o{ funds : classifies
    funds ||--o{ holdings : holds
    submissions ||--o{ holdings : files
    
    control_definitions ||--o{ control_executions : executes
    control_definitions ||--o{ control_exceptions : generates
    control_executions ||--o{ control_exceptions : produces
    funds ||--o{ control_exceptions : flags
    holdings ||--o{ control_exceptions : flags
    
    control_exceptions ||--o{ remediation_items : remedies
    control_exceptions ||--o{ control_exceptions : tracks_repeat
    
    funds ||--o{ risk_assessments : assesses
    control_definitions ||--o{ kci_snapshots : measures
```

### 4.1 Relational Tables Inventory

| Table Name | Primary Key | Key Foreign Keys | Purpose |
|---|---|---|---|
| `ingestion_runs` | `id` (SERIAL) | None | Tracks SEC ZIP download, SHA-256 hash, execution time, and ingestion mode. |
| `submissions` | `accession_number` (VARCHAR) | `ingestion_run_id` | Unique regulatory filings filed under SEC EDGAR accession numbering. |
| `registrants` | `cik` (VARCHAR) | None | Investment companies / trusts registered with the SEC. |
| `fund_series` | `series_id` (VARCHAR) | `cik` | Fund series entities identified by SEC Series ID (`S0000xxxxx`). |
| `funds` | `id` (SERIAL) | `accession_number`, `series_id`, `cik` | Individual fund-level reported balance sheets (Total Assets, Net Assets, Liabilities). |
| `holdings` | `id` (SERIAL) | `accession_number`, `fund_id` | Granular security-level position schedule (6,025,567 rows in full dataset). |
| `reporting_periods`| `id` (SERIAL) | None | Calendar quarterly rollup of fund and holding counts per report date. |
| `control_definitions`| `control_id` (VARCHAR) | None | Catalog of 16 controls, risk categories, frequencies, and baseline thresholds. |
| `control_executions` | `id` (SERIAL) | `control_id` | Audit records of each control run (scanned count, pass rate, duration, metadata). |
| `control_exceptions` | `id` (SERIAL) | `control_id`, `execution_id`, `fund_id`, `holding_id` | Detected exceptions with severity, risk scores, status, root cause, and JSON evidence. |
| `risk_assessments` | `id` (SERIAL) | `fund_id` | Snapshot of fund-level inherent risk, control effectiveness, and residual risk. |
| `kri_snapshots` | `id` (SERIAL) | None | Historical snapshots of the 7 Key Risk Indicators (value, RAG status, trend). |
| `kci_snapshots` | `id` (SERIAL) | `control_id` | Historical snapshots of the 7 Key Control Indicators. |
| `kpi_snapshots` | `id` (SERIAL) | None | Historical snapshots of the 8 Operational Key Performance Indicators. |
| `remediation_items`| `id` (SERIAL) | `exception_id` | Remediation action items, assigned owners, due dates, and validation status. |
| `audit_events` | `id` (SERIAL) | None | Append-only immutable log of every action, actor, timestamp, and JSON diff. |
| `users` | `id` (SERIAL) | None | System users and analysts with role-based access levels. |
| `ai_analysis` | `id` (SERIAL) | None | Audit log of all AI prompts, evidence hashes, LLM responses, and validation flags. |
| `data_quality_results`| `id` (SERIAL) | `ingestion_run_id` | Summary scores and rejected record metrics for ingestion batches. |
| `reference_data` | `id` (SERIAL) | None | Lookups for asset categories, issuer types, and root-cause taxonomies. |

### 4.2 Key Column Specifications & Constraints
- **`holdings.balance` vs `holdings.value`:**
  - `balance`: `NUMERIC(20,4)` represents physical share or unit count (can be negative for short sale obligations).
  - `value`: `NUMERIC(20,2)` represents USD fair value of the position.
- **`holdings.pct_val`:** `NUMERIC(10,6)` percentage of net assets represented by the position.
- **`control_exceptions.risk_level`:** `VARCHAR(30)` constrained to `CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'INSUFFICIENT_EVIDENCE'))`.
- **`control_exceptions.status`:** `VARCHAR(30)` constrained to `CHECK (status IN ('DETECTED', 'TRIAGED', 'ASSIGNED', 'INVESTIGATING', 'REMEDIATION_PLANNED', 'REMEDIATION_IN_PROGRESS', 'VALIDATION', 'CLOSED', 'ACCEPTED'))`.
- **Natural Unique Keys:**
  - `holdings(accession_number, holding_id)`: Enforces natural idempotency.
  - `funds(accession_number, series_id)`: Prevents duplicate fund series reporting in the same accession.
  - `kri_snapshots(kri_id, period_date)`: Ensures single authoritative metric snapshot per period.

---

## 5. Data Ingestion & Normalization Pipeline

### 5.1 Ingestion Architecture
The platform features two operational ingestion pathways:
1. **Interactive / Modular Ingestion (`backend/ingestion/pipeline.py`):** Used during standard app lifecycle or `--sample` demonstration runs. Utilizes Pandas chunking (`chunksize=10000`) and SQLAlchemy parameterized inserts.
2. **High-Performance Full-Population Ingestion (`scripts/ingest_full.py`):** Purpose-built binary streaming engine for loading the entire SEC quarterly dataset (6,000,000+ rows) without memory exhaustion.

### 5.2 Performance & Throughput Benchmark
The ingestion pipeline was verified against the official SEC DERA Q3 2025 archive:
- **Archive File:** `2025q3_nport.zip` (468,940,747 bytes / 447.2 MB compressed)
- **SHA-256 Checksum:** `4cc5c2431bf8997ef0af1cb7b69568255a1d6a1840e41499d9ffd1fc42e030f6`
- **Total Holdings Loaded:** **6,025,567 rows**
- **Ingestion Time:** **175.75 seconds (2.93 minutes)**
- **Throughput:** **34,284 holdings/second**
- **Peak Process Memory:** **89.08 MB** (monitored via Python `tracemalloc`)
- **Index Build Duration:** **15.91 seconds** across 9 composite indexes

### 5.3 Streaming Optimization Strategy (`ingest_full.py`)
To achieve 34,284 rows/sec with under 90 MB RAM, the pipeline implements four specific engineering patterns:
1. **Direct Stream Parsing:** Reads `FUND_REPORTED_HOLDING.tsv` directly from inside the `.zip` archive via Python `zipfile.ZipFile.open()`, avoiding uncompressing 2.5 GB of raw TSV text to disk.
2. **Accession-to-Fund Map in Memory:** Pre-loads a single dictionary of `accession_number -> fund_id` (13,199 integer entries, taking <2 MB RAM) to perform immediate foreign-key resolution without expensive database joins during streaming.
3. **Index Suspension & Bulk Rebuild:** Drops all 9 secondary indexes on `holdings` prior to the copy stream, bulk-inserts clean TSV chunks using PostgreSQL native `COPY FROM` (via `psycopg2.cursor.copy_from`), and rebuilds all indexes concurrently after insertion.
4. **Buffered TSV In-Memory Streaming:** Buffers 100,000 sanitized TSV lines into an in-memory `io.StringIO` buffer before piping to `copy_from`, minimizing socket round-trips while bounding RAM usage.

### 5.4 Data Normalization Rules (`normalizer.py`)
- **CUSIP Normalization:** Strips leading/trailing whitespace, converts to uppercase, and truncates to 9 characters.
- **LEI Normalization:** Normalizes 20-character Legal Entity Identifiers; strips literal `'N/A'` or `'NONE'` strings to `NULL`.
- **Numeric Fields:** Replaces empty strings or non-numeric strings with `\N` (PostgreSQL `NULL`) to preserve type safety.
- **String Cleaning:** Sanitizes tab characters (`\t`), newlines (`\n`, `\r`), and unescaped backslashes (`\`) inside issuer titles and security descriptions to prevent TSV delimitation corruption.
- **Restricted Securities:** Maps SEC boolean indicators (`'Y'`/`'N'`) to PostgreSQL booleans (`'t'`/`'f'`).

---

## 6. Deterministic Control Framework (16 Controls)

The platform implements **16 automated, deterministic controls** categorized across 7 risk domains. Every control executes parameterized SQL queries, computes coverage and testability ratios, categorizes findings under the 4-tier taxonomy, and calculates explainable risk scores.

```mermaid
pie title Control Distribution by Domain (16 Total)
    "Data Quality (DQ)" : 4
    "Concentration (CONC)" : 4
    "Reconciliation (REC)" : 2
    "Valuation (VAL)" : 2
    "Reporting (RPT)" : 2
    "Liquidity (LIQ)" : 1
    "Classification (CLS)" : 1
```

### 6.1 Control Specifications Summary

| ID | Control Name | Risk Domain | Data Requirements | Logic & Evaluation Method | Phase 3 Full Dataset Pass Rate |
|---|---|---|---|---|---|
| **DQ-001** | Missing Required Fields | Data Quality | `name`, `value`, `cusip`, `isin` | Flags holdings where security name, value, or both CUSIP and ISIN are NULL. | 99.93% (1,540 exceptions) |
| **DQ-002** | Duplicate Holdings | Data Quality | `accession_number`, `cusip`, `name` | Detects duplicate holdings within the same accession grouping by natural keys. | 100.00% (0 exceptions) |
| **DQ-003** | Invalid Values | Data Quality | `balance`, `pct_val`, `units` | Checks for impossible percentages ($>100\%$ or $<-100\%$) and invalid values. | 99.93% (1,540 exceptions) |
| **DQ-004** | Classification Consistency | Data Quality | `asset_cat`, `issuer_cat` | Verifies that reported codes exist in authoritative SEC N-PORT reference categories. | 100.00% (0 exceptions) |
| **REC-001** | Period Reconciliation | Reconciliation | `holdings.value (T)`, `holdings.value (T-1)` | Compares common CUSIP positions between periods; flags position value change $>50\%$. | Not Testable (0.0% coverage) |
| **REC-002** | Portfolio Completeness | Reconciliation | `funds.total_assets`, `holdings.value` | Compares sum of holdings values vs reported fund total assets ($\pm 10.0\%$ tolerance). | 90.34% (637 analytical exc.) |
| **VAL-001** | Stale / Zero Prices | Valuation | `holdings.balance`, `holdings.value` | Identifies positions where balance $>0$ but fair value is reported as $\$0.00$. | 99.95% (1,079 exceptions) |
| **VAL-002** | Extreme Price Movements | Valuation | `implied_price (T)`, `implied_price (T-1)` | Detects period-over-period implied price ($\frac{\text{value}}{\text{balance}}$) swings exceeding $\pm 50\%$. | 100.00% (0 exceptions) |
| **CONC-001**| Position Concentration | Concentration | `holdings.pct_val` | Calculates Top-1, Top-5, Top-10 concentration per fund (Amber $>35\%$, Red $>45\%$). | 90.58% (622 exceptions) |
| **CONC-002**| Issuer Concentration | Concentration | `holdings.lei`, `holdings.name` | Aggregates holding values by single issuer (Amber $>25\%$, Red $>35\%$). | 88.02% (791 exceptions) |
| **CONC-003**| Asset Class Concentration| Concentration | `holdings.asset_cat` | Flags fund exposure to a single asset category exceeding $>80\%$. | 79.59% (1,347 exceptions) |
| **CONC-004**| Geographic Concentration| Concentration | `holdings.investment_country`| Flags fund country-level allocation exceeding $>85\%$. | 72.82% (1,794 exceptions) |
| **LIQ-001** | Liquidity Proxy | Liquidity | `asset_cat`, `issuer_cat`, `pct_val`| Classifies holdings into liquidity tiers; flags illiquid allocation $>15\%$ Amber, $>25\%$ Red. | 99.30% (46 exceptions) |
| **RPT-001** | Reporting Timeliness | Reporting | `filing_date`, `period_of_report` | Measures days between period end and filing date (Amber $>60$ days, Red $>90$ days). | 98.70% (86 exceptions) |
| **RPT-002** | Reporting Gaps | Reporting | `fund_series.series_id`, calendar | Detects missing sequential quarterly filings for established active fund series. | 100.00% (0 exceptions) |
| **CLS-001** | Classification Changes | Data Quality | `asset_cat (T)`, `asset_cat (T-1)` | Detects period-over-period security reclassifications (asset/issuer categories). | 100.00% (0 exceptions) |

### 6.2 Deep Dive into Critical Controls

#### REC-002: Portfolio Completeness
- **Objective:** Verify that the aggregated fair value of reported portfolio holdings reconciles with the fund's gross reported total assets.
- **SQL Logic:**
  ```sql
  SELECT f.id, f.fund_name, f.total_assets,
         COALESCE(SUM(h.value), 0) as holdings_total,
         COUNT(h.id) as holding_count
  FROM funds f
  LEFT JOIN holdings h ON h.fund_id = f.id
  WHERE f.period_of_report = :period_date
    AND f.total_assets IS NOT NULL AND f.total_assets > 0
  GROUP BY f.id, f.fund_name, f.total_assets;
  ```
- **Operational Reality & Analytical Tolerance:**
  A $10.0\%$ analytical tolerance is applied. In mutual fund accounting, discrepancies between gross total assets and security schedules typically stem from:
  1. Cash equivalents and short-term receivables/payables not scheduled as securities.
  2. Derivative contracts reported as net unrealized gain/loss rather than notional asset values.
  3. Closed-end funds with debt leverage facilities.
- **Handling Funds without Holdings:**
  If `holding_count == 0`, the fund is not marked as a failed reconciliation. Instead, it is classified under `DATA_AVAILABILITY` with status `INSUFFICIENT_EVIDENCE` (Score 0).

#### CONC-001: Position Concentration
- **Objective:** Monitor portfolio concentration to prevent catastrophic single-position drawdowns.
- **SQL Window Function:**
  ```sql
  WITH ranked_holdings AS (
      SELECT h.fund_id, f.fund_name, h.pct_val,
             ROW_NUMBER() OVER (PARTITION BY h.fund_id ORDER BY h.pct_val DESC NULLS LAST) as rn
      FROM holdings h
      JOIN funds f ON h.fund_id = f.id
      WHERE f.period_of_report = :period_date AND h.pct_val > 0
  )
  SELECT fund_id, fund_name,
         MAX(CASE WHEN rn = 1 THEN pct_val END) as top1_pct,
         SUM(CASE WHEN rn <= 5 THEN pct_val ELSE 0 END) as top5_pct,
         SUM(CASE WHEN rn <= 10 THEN pct_val ELSE 0 END) as top10_pct
  FROM ranked_holdings
  GROUP BY fund_id, fund_name
  HAVING SUM(CASE WHEN rn <= 10 THEN pct_val ELSE 0 END) > 35.0;
  ```
- **Thresholds:** Green: $\le 35\%$, Amber: $35\% - 45\%$, Red: $> 45\%$.

#### VAL-001: Stale / Zero Pricing
- **Objective:** Detect operational valuation failures where security balances exist but reported fair value is $\$0.00$.
- **Real-World Finding:** Successfully detects sanctioned holdings (such as Russian ADRs held under trading halts) and defaulted private loans held at zero valuation.

---

## 7. Exception Integrity & 4-Tier Taxonomy

A critical breakthrough of the platform is the elimination of sample-data artifacts and data-availability false positives through a rigorous 4-tier exception taxonomy.

```mermaid
flowchart TD
    BREAK{"Discrepancy / Break Detected"}
    
    BREAK --> Q1{"Is baseline data available\nin the reporting filing?"}
    Q1 -- No --> DA["DATA_AVAILABILITY\n(Status: INSUFFICIENT_EVIDENCE)\n(Risk Score: 0)"]
    Q1 -- Yes --> Q2{"Is source data malformed\nor schema-violating?"}
    
    Q2 -- Yes --> DQ["DATA_QUALITY_EXCEPTION\n(Negative balance, missing CUSIP, invalid type)\n(Severity: LOW to HIGH)"]
    Q2 -- No --> Q3{"Did control execution encounter\nunhandled software crash?"}
    
    Q3 -- Yes --> CF["CONTROL_FAILURE\n(Status: FAILED)\n(Requires Engineering Action)"]
    Q3 -- No --> AE["ANALYTICAL_EXCEPTION\n(Genuine portfolio break: concentration, recon break)\n(Severity: Scored 1-125)"]
```

### 7.1 Taxonomy Definitions

1. **`ANALYTICAL_EXCEPTION`:**
   - **Definition:** A genuine portfolio-level condition that violates an analytical threshold (e.g., top-10 concentration $>45\%$, filing delay $>60$ days, or gross assets vs. holdings variance $>10\%$).
   - **Risk Treatment:** Scored deterministically using the $1\text{--}125$ risk formula.
2. **`DATA_QUALITY_EXCEPTION`:**
   - **Definition:** A defect in the reported filing data (e.g., missing mandatory security identifiers, negative share quantities representing unflagged short positions).
   - **Risk Treatment:** Scored and routed to data stewardship remediation.
3. **`DATA_AVAILABILITY`:**
   - **Definition:** An analytical test could not be completed because underlying filings omitted schedules (e.g., SEC Part C omitted by 3 funds) or the baseline historical quarter ($T-1$) was not present in a single-quarter ingestion.
   - **Risk Treatment:** Assigned `INSUFFICIENT_EVIDENCE` and Risk Score `0`. Excluded from KRI failure denominators to avoid artificial alarm inflation.
4. **`CONTROL_FAILURE`:**
   - **Definition:** An unhandled execution failure (database timeout, schema mismatch) preventing the control query from running.
   - **Risk Treatment:** Captured in `control_executions` with `status = 'FAILED'`, triggering operational engineering intervention.

### 7.2 Resolution of the Phase 2 Artifact
- **Phase 2 Problem:** In Phase 2, testing against a partial 5,000-holding sample left 6,547 of 6,600 funds with $\$0$ holdings in the database. `REC-002` flagged all 6,547 funds as failed reconciliations, skewing `KRI-002` to $99.9\%$ (RED).
- **Phase 3 Resolution:** With all 6,025,567 holdings ingested, `REC-002` pass rate rose to **$90.34\%$** (637 genuine analytical exceptions + 3 data availability exceptions). `KRI-002` dropped to a realistic **$9.70\%$ (AMBER)**.

---

## 8. Risk Scoring & Residual Risk Modeling

Risk assessment in AWM ControlWatch is strictly deterministic. The platform explicitly prohibits machine learning or large language models from inventing or modifying authoritative risk scores.

### 8.1 Inherent Risk Formula
Inherent risk represents the raw operational exposure before considering control safeguards:
$$\text{Inherent Risk} = \text{Impact} \times \text{Likelihood} \quad (\text{Scale: } 1 \text{ to } 25)$$

- **Impact ($1\text{--}5$):** Financial materiality or portfolio distortion.
- **Likelihood ($1\text{--}5$):** Probability of recurrence or systemic persistence.

### 8.2 Exception Risk Score Formula
Every generated exception is scored using the 3-factor operational risk equation:
$$\text{Risk Score} = \text{Impact} \times \text{Likelihood} \times (6 - \text{Control Effectiveness}) \quad (\text{Scale: } 1 \text{ to } 125)$$

#### Threshold Mapping
- **LOW:** $1 \le \text{Score} < 25$
- **MEDIUM:** $25 \le \text{Score} < 50$
- **HIGH:** $50 \le \text{Score} < 75$
- **CRITICAL:** $75 \le \text{Score} \le 125$
- **INSUFFICIENT_EVIDENCE:** Score $= 0$ (Reserved for `DATA_AVAILABILITY`)

### 8.3 Residual Risk Reduction Model
Residual risk models the remaining exposure after factoring in the effectiveness of operational controls:
$$\text{Residual Risk} = \text{Inherent Risk} \times (1 - \text{Control Effectiveness}_{\text{normalized}})$$
Where $\text{Control Effectiveness}_{\text{normalized}} \in [0.0, 0.8]$ is derived from the control's historical execution rate and pass rate.

---

## 9. Metrics Engine (KRIs, KCIs, and KPIs)

The metrics engine calculates and snapshots **22 distinct operational metrics** per reporting period, maintaining complete mathematical lineage back to source control executions.

### 9.1 Key Risk Indicators (KRIs) — 7 Metrics

| KRI ID | Indicator Name | Formula / Logic | Green | Amber | Red | Phase 3 Value | Status |
|---|---|---|---|---|---|---|---|
| **KRI-001** | Concentration Exposure | $\max(\text{Top-10 Holding } \%)$ across all funds | $<35\%$ | $35\text{--}45\%$ | $>45\%$ | 80.51% | 🔴 RED |
| **KRI-002** | Reconciliation Exception Rate | $\frac{\text{Analytical Recon Exceptions}}{\text{Testable Reconciliations}} \times 100$ | $<5\%$ | $5\text{--}15\%$ | $>15\%$ | 9.70% | 🟡 AMBER |
| **KRI-003** | Data Quality Exception Rate | $\frac{\text{DQ Exceptions}}{\text{Records Scanned}} \times 100$ | $<2\%$ | $2\text{--}10\%$ | $>10\%$ | 0.07% | 🟢 GREEN |
| **KRI-004** | Valuation Anomaly Rate | $\frac{\text{Valuation Exceptions}}{\text{Valued Holdings}} \times 100$ | $<3\%$ | $3\text{--}10\%$ | $>10\%$ | 0.05% | 🟢 GREEN |
| **KRI-005** | Reporting Timeliness | Average filing delay (in days) | $<45\text{d}$ | $45\text{--}75\text{d}$ | $>75\text{d}$ | 56.07d | 🟡 AMBER |
| **KRI-006** | Exception Aging | Average age (in days) of open exceptions | $<14\text{d}$ | $14\text{--}30\text{d}$ | $>30\text{d}$ | 0.00d | 🟢 GREEN |
| **KRI-007** | Repeat Exception Rate | $\frac{\text{Repeat Exceptions}}{\text{Total Exceptions}} \times 100$ | $<5\%$ | $5\text{--}15\%$ | $>15\%$ | 0.00% | 🟢 GREEN |

### 9.2 Key Control Indicators (KCIs) — 7 Metrics
- **KCI-001 Control Execution Rate:** $100.0\%$ (16 executed / 16 active controls).
- **KCI-002 Control Pass Rate:** $37.5\%$ (executions with 0 exceptions / 16 total controls).
- **KCI-003 Control Failure Rate:** $0.0\%$ (no execution crashes).
- **KCI-004 Evidence Completeness:** $100.0\%$ (all 7,393 exceptions contain structured JSON evidence).
- **KCI-005 Repeat Control Failure Rate:** $0.0\%$.
- **KCI-006 Overdue Remediation Rate:** $0.0\%$.
- **KCI-007 Control Coverage:** $100.0\%$ (all controls evaluated this period).

### 9.3 Key Performance Indicators (KPIs) — 8 Metrics
- **KPI-001 Funds Processed:** 6,600 funds.
- **KPI-002 Holdings Processed:** 6,025,567 holdings.
- **KPI-003 Total Records Processed:** 6,025,567 source rows.
- **KPI-004 Controls Executed:** 16 executions.
- **KPI-005 Exceptions Generated:** 7,393 exceptions (3,295 analytical, 1,540 data quality, 2,558 data availability).
- **KPI-006 Avg Processing Time:** 830.63 ms per control.
- **KPI-007 Remediation Turnaround:** 0.00 days.
- **KPI-008 Automation Coverage:** $100.0\%$ (all controls automated).

---

## 10. Exception Lifecycle & Remediation Workflow

The platform enforces an **8-stage state machine** for exception resolution, backed by mandatory audit trail generation.

```mermaid
stateDiagram-v2
    [*] --> DETECTED
    DETECTED --> TRIAGED : Analyst Reviews
    DETECTED --> ACCEPTED : Risk Accepted
    DETECTED --> CLOSED : False Alarm
    
    TRIAGED --> ASSIGNED : Assign Owner
    TRIAGED --> ACCEPTED : Risk Accepted
    TRIAGED --> CLOSED : Deemed Immaterial
    
    ASSIGNED --> INVESTIGATING : Analysis Starts
    ASSIGNED --> ACCEPTED : Risk Accepted
    
    INVESTIGATING --> REMEDIATION_PLANNED : Create Action Item
    INVESTIGATING --> ACCEPTED : Risk Accepted
    INVESTIGATING --> CLOSED : Root Cause Resolved
    
    REMEDIATION_PLANNED --> REMEDIATION_IN_PROGRESS : Work Underway
    
    REMEDIATION_IN_PROGRESS --> VALIDATION : Implementation Done
    
    VALIDATION --> CLOSED : Validation Passes
    VALIDATION --> REMEDIATION_IN_PROGRESS : Validation Fails
    
    CLOSED --> [*]
    ACCEPTED --> [*]
```

### 10.1 Permitted Transitions & State Rules
Transitions outside `VALID_TRANSITIONS` raise an immediate `ValueError` and are rolled back:
```python
VALID_TRANSITIONS = {
    "DETECTED": ["TRIAGED", "ACCEPTED", "CLOSED"],
    "TRIAGED": ["ASSIGNED", "ACCEPTED", "CLOSED"],
    "ASSIGNED": ["INVESTIGATING", "ACCEPTED"],
    "INVESTIGATING": ["REMEDIATION_PLANNED", "ACCEPTED", "CLOSED"],
    "REMEDIATION_PLANNED": ["REMEDIATION_IN_PROGRESS"],
    "REMEDIATION_IN_PROGRESS": ["VALIDATION"],
    "VALIDATION": ["CLOSED", "REMEDIATION_IN_PROGRESS"],
    "CLOSED": [],
    "ACCEPTED": []
}
```

### 10.2 Root Cause Taxonomy
Root causes must be classified under standardized categories:
`DATA_QUALITY`, `PROCESS_FAILURE`, `TECHNOLOGY_FAILURE`, `REFERENCE_DATA`, `HUMAN_PROCESS_INPUT`, `EXTERNAL_EVENT`, or `UNKNOWN`.

### 10.3 Immutable Audit Trail (`audit_events`)
Every transition, assignment, or remediation edit automatically writes an append-only entry to `audit_events` capturing:
- `timestamp`: UTC timestamp.
- `actor`: Username of the initiating analyst or `'SYSTEM'`.
- `action`: State change description.
- `old_value` / `new_value`: Full JSON snapshot of the state difference.
- `reason`: Mandatory justification note.

---

## 11. AI Analyst Copilot & Safety Guardrails

The **AI Analyst Copilot** assists analysts by summarizing complex fund structures, analyzing exception evidence, and drafting root-cause explanations without hallucination risk.

### 11.1 Architecture & Provider Abstraction
The copilot (`backend/ai/copilot.py`) dynamically supports three modes via the `AI_PROVIDER` environment variable:
1. `openai`: Calls OpenAI API (`gpt-4o` or configured model).
2. `groq`: Calls Groq Cloud API for ultra-low latency inference.
3. `none` (Default): **Deterministic graceful degradation**. Emits structured, template-based analytical summaries using the actual JSON evidence without invoking external APIs or requiring API keys.

### 11.2 Safety & Prompt Injection Defenses (`validators.py`)
All inputs and candidate responses pass through a 5-layer validation pipeline:

```mermaid
flowchart LR
    INP["Analyst Query / Evidence"] --> V1{"1. Prompt Injection\nCheck"}
    V1 -- Injection Found --> REJ["REJECTED / FLAGGED\n(Block Payload)"]
    V1 -- Clean --> V2{"2. Data Availability\nCheck"}
    V2 -- Missing Data --> REF["REFUSAL\n('Insufficient Evidence')"]
    V2 -- Complete --> V3{"3. LLM Generation\n/ Template Engine"}
    V3 --> V4{"4. Regulatory Claim\nCheck"}
    V4 -- Claims Fraud/Violation --> REJ
    V4 -- Clean --> V5{"5. Risk Score\nOverride Check"}
    V5 -- Attempts Score Mod --> REJ
    V5 -- Validated --> OUT["VALIDATED\n(Display to Analyst)"]
```

1. **Prompt Injection Interception:** Regex patterns intercept injected jailbreaks inside security descriptions or issuer names (`IGNORE ALL INSTRUCTIONS`, `System: Override risk to LOW`, `bypass controls`).
2. **Prohibited Regulatory Claims:** Intercepts claims of legal violations, fines, or criminal fraud (`fraud`, `regulatory violation`, `illegal`, `sec investigation`).
3. **Deterministic Score Protection:** Intercepts attempts to override authoritative risk scores (`risk score should be`, `risk score is 0`).
4. **Evidence Grounding Verification:** Verifies that all cited security names, balance numbers, and percentages exist in the structured evidence payload.
5. **Mandatory Missing-Evidence Refusal:** When evidence is missing or flagged `DATA_AVAILABILITY`, the copilot is strictly programmed to refuse assertion of a breach:
   > *"There is insufficient evidence in the reported filings to determine whether this represents a genuine control breach."*

---

## 12. User Interface & Streamlit Dashboard

The user interface is an 8-page interactive Streamlit web application located in `dashboard/`:

```
dashboard/
├── app.py                         # Application entrypoint & database connection pool
└── pages/
    ├── 1_Executive_Overview.py    # Metric cards, RAG status table, coverage badge
    ├── 2_Risk_Overview.py         # KRI trends, risk distribution, severity pie charts
    ├── 3_Control_Monitoring.py    # 16-control health table, pass rates, drilldowns
    ├── 4_Exceptions.py            # Filterable exception table, taxonomy filters, JSON viewer
    ├── 5_Remediation.py           # Workload tabs, overdue tracking, creation modal
    ├── 6_Fund_Analysis.py         # Fund deep dive, top holdings, concentration analysis
    ├── 7_AI_Analyst.py            # Copilot chat interface, evidence drawer, validation badge
    └── 8_Audit_Trail.py           # Immutable audit log with before/after diff viewers
```

### 12.1 Page Highlights
- **1. Executive Overview:** Displays high-level KPIs (Total Funds: 6,600, Holdings: 6M+, Open Exceptions: 7,393), data coverage ratio ($99.95\%$), and RAG status cards.
- **4. Exceptions:** Features a dedicated multi-select taxonomy filter (`ANALYTICAL_EXCEPTION`, `DATA_QUALITY_EXCEPTION`, `DATA_AVAILABILITY`) allowing analysts to isolate genuine portfolio issues from baseline filing omissions.
- **7. AI Analyst:** Features pre-built operational query buttons (*"Summarize Fund"*, *"Explain KRI"*, *"Analyze Priority Exceptions"*), an evidence inspection drawer, and real-time validation badges.

---

## 13. FastAPI REST Interface

The backend is built with FastAPI (`backend/main.py`), offering OpenAPI documentation (`/docs`), automated CORS middleware, and process timing headers (`X-Process-Time-Ms`).

### 13.1 Endpoint Catalog

| Method | Path | Router Module | Description |
|---|---|---|---|
| `GET` | `/health` | `main.py` | System health check, database connectivity, and active AI provider. |
| `GET` | `/funds` | `api/funds.py` | Paginated fund list with search by name, series ID, or CIK. |
| `GET` | `/funds/{id}` | `api/funds.py` | Fund balance sheet, series info, and aggregate holdings summary. |
| `GET` | `/holdings` | `api/holdings.py` | Filterable holdings search by fund, CUSIP, ISIN, asset class, or country. |
| `GET` | `/controls` | `api/controls.py` | List all 16 registered controls with threshold configurations. |
| `POST`| `/controls/run` | `api/controls.py` | Execute all or specific controls for a designated reporting period. |
| `GET` | `/controls/executions` | `api/controls.py`| Historical control execution logs, scanned records, and pass rates. |
| `GET` | `/exceptions` | `api/exceptions.py`| Paginated exceptions with filtering by severity, status, control, and taxonomy. |
| `POST`| `/exceptions/{id}/transition` | `api/exceptions.py`| Advance exception through lifecycle with mandatory audit logging. |
| `POST`| `/exceptions/{id}/assign` | `api/exceptions.py`| Assign exception to an operational analyst. |
| `GET` | `/kris` | `api/metrics.py` | Current and historical KRI snapshots with RAG status and trend. |
| `GET` | `/kcis` | `api/metrics.py` | Current and historical KCI snapshots. |
| `GET` | `/kpis` | `api/metrics.py` | Operational performance KPIs. |
| `GET` | `/audit-events` | `api/audit.py` | Query append-only audit trail filtered by actor, object, or date range. |
| `POST`| `/ai/analyze` | `api/ai_routes.py` | Submit evidence-grounded query to AI copilot with validation check. |
| `POST`| `/ingestion/run` | `api/ingestion_routes.py`| Trigger SEC quarterly dataset download and ingestion. |

---

## 14. Technology Stack & Dependency Inventory

### 14.1 Core Technologies
- **Runtime Environment:** Python 3.9.6 / 3.12+
- **Database Engine:** PostgreSQL 16 (Relational Engine with JSONB support)
- **API Framework:** FastAPI 0.115.6 + Uvicorn 0.34.0
- **Database Connectivity:** SQLAlchemy 2.0.36 + psycopg2-binary 2.9.10
- **Data Engineering:** Pandas 2.2.3 + NumPy 2.2.1
- **User Interface:** Streamlit 1.41.1 + Plotly Express 5.24.1
- **AI Integrations:** OpenAI SDK 1.58.1 + Groq SDK 0.13.0
- **Testing:** Pytest 8.4.2 + Pytest-Cov 7.1.0 + AnyIO 4.12.1
- **Logging & Resilience:** Structlog 24.4.0 + Tenacity 9.0.0
- **Containerization:** Docker Multi-stage + Docker Compose

### 14.2 Dependency File (`requirements.txt`)
```ini
# Backend
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
psycopg2-binary>=2.9.10
alembic==1.14.1
pydantic==2.10.4
pydantic-settings==2.7.1
python-dotenv==1.0.1
httpx==0.28.1

# Data Processing
pandas==2.2.3
numpy==2.2.1

# Dashboard
streamlit==1.41.1
plotly==5.24.1

# AI
openai==1.58.1
groq==0.13.0

# Testing
pytest==8.3.4
pytest-cov==6.0.0
pytest-asyncio==0.25.0

# Utilities
structlog==24.4.0
tenacity==9.0.0
python-multipart==0.0.20
```

---

## 15. Installation, Configuration & Deployment

### 15.1 Configuration Variables (`.env`)

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://awm:awm_password@localhost:5432/awm_controlwatch` | SQLAlchemy database connection string. |
| `POSTGRES_USER`| `awm` | PostgreSQL database username. |
| `POSTGRES_PASSWORD`| `awm_password` | PostgreSQL database user password. |
| `POSTGRES_DB` | `awm_controlwatch` | PostgreSQL database name. |
| `AI_PROVIDER` | `none` | AI mode: `'none'`, `'openai'`, or `'groq'`. |
| `OPENAI_API_KEY`| `""` | API key for OpenAI (if provider is `'openai'`). |
| `GROQ_API_KEY` | `""` | API key for Groq (if provider is `'groq'`). |
| `SEC_DATA_DIR` | `./data` | Directory for caching downloaded SEC ZIP files. |
| `API_PORT` | `8000` | Port for FastAPI backend. |
| `STREAMLIT_PORT`| `8501` | Port for Streamlit dashboard. |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

### 15.2 Local Virtual Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/raghavkhetarpal/control-watch.git
cd control-watch

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install locked dependencies
pip install -r requirements.txt

# 4. Initialize local PostgreSQL database
createdb awm_controlwatch
psql -d awm_controlwatch -f backend/database/schema.sql

# 5. Populate reference data & run bootstrap
PYTHONPATH=. python scripts/bootstrap.py --sample 5000
```

### 15.3 Full Production Ingestion & Control Run

```bash
# Ingest full 6M+ holdings from official SEC Q3 2025 archive
PYTHONPATH=. python scripts/ingest_full.py

# Run coverage analysis audit
PYTHONPATH=. python scripts/analyze_coverage.py

# Execute all 16 controls across the full dataset
PYTHONPATH=. python scripts/run_controls.py --period 2025-06-30
```

### 15.4 Launching Services

```bash
# Terminal 1: Launch FastAPI Backend
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Launch Streamlit Dashboard
PYTHONPATH=. streamlit run dashboard/app.py --server.port 8501
```

- **Dashboard UI:** `http://localhost:8501`
- **Interactive OpenAPI Documentation:** `http://localhost:8000/docs`
- **System Health Endpoint:** `http://localhost:8000/health`

### 15.5 Containerized Deployment (Docker Compose)

```bash
# Build and run entire stack (PostgreSQL + FastAPI + Streamlit)
docker-compose up -d --build

# Run bootstrap in backend container
docker-compose exec backend python scripts/bootstrap.py --sample 5000
```

---

## 16. Verification, Quality Assurance & Test Suite

The system includes a **96-test automated verification suite** with 100% pass rate in under 1 second.

```bash
$ PYTHONPATH=. pytest tests/ -v --cov=backend
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/raghav/Desktop/Projects/awm
plugins: anyio-4.12.1, asyncio-1.2.0, cov-7.1.0

collected 96 items

tests/ai/test_ai_validation.py .........                                 [  9%]
tests/api/test_api.py ......                                             [ 15%]
tests/controls/test_concentration.py ..                                  [ 17%]
tests/controls/test_data_quality.py .....                                [ 22%]
tests/controls/test_reconciliation.py ...                                [ 26%]
tests/integration/test_metrics.py ...                                    [ 29%]
tests/integration/test_pipeline.py ....                                  [ 33%]
tests/unit/test_ai_copilot.py ........                                   [ 41%]
tests/unit/test_controls_logic.py ........                               [ 50%]
tests/unit/test_data_availability_semantics.py ....                      [ 54%]
tests/unit/test_exception_manager_unit.py .......                        [ 61%]
tests/unit/test_exception_workflow.py ....                               [ 65%]
tests/unit/test_ingestion_validators.py ....                             [ 69%]
tests/unit/test_metrics_engine.py .....                                  [ 75%]
tests/unit/test_remediation_tracker.py ......                            [ 81%]
tests/unit/test_residual_risk.py ...                                     [ 84%]
tests/unit/test_risk_scoring.py .....                                    [ 89%]
tests/unit/test_risk_taxonomy.py ...                                     [ 92%]
tests/unit/test_severity.py ....                                         [ 96%]
tests/unit/test_thresholds.py ...                                        [100%]

======================== 96 passed, 2 warnings in 0.28s ========================
```

### 16.1 Test Suite Organization

| Directory / File | Test Count | Scope of Verification |
|---|---|---|
| `tests/ai/test_ai_validation.py` | 9 | Interception of 5 prompt-injection patterns, hallucination detection, regulatory claims block, and score override block. |
| `tests/api/test_api.py` | 6 | FastAPI endpoints (`/health`, `/funds`, `/controls`, `/exceptions`, `/kris`). |
| `tests/controls/` | 10 | Data quality (DQ-001..004), reconciliation (REC-001..002), and concentration (CONC-001). |
| `tests/integration/` | 7 | End-to-end normalization, data validator schema checks, metric calculations. |
| `tests/unit/test_data_availability_semantics.py` | 4 | Data availability classification, 0-score assignment, refusal logic. |
| `tests/unit/test_risk_scoring.py` | 5 | Boundary conditions of the $1\text{--}125$ risk score equation. |
| `tests/unit/test_residual_risk.py` | 3 | Verification of inherent vs. residual risk mathematical formulas. |
| `tests/unit/test_exception_workflow.py` | 4 | State machine valid/invalid transitions, terminal state immutability. |
| `tests/unit/test_remediation_tracker.py` | 6 | Action item creation, status progression, validation results. |
| `tests/unit/` (other modules) | 42 | Ingestion validators, threshold evaluators, taxonomy mappings, copilot fallbacks. |

---

## 17. Engineering Design Rationale

| Architecture Decision | Option Selected | Alternative Rejected | Rationale |
|---|---|---|---|
| **Storage Engine** | PostgreSQL 16 Relational Engine | MongoDB / Document DB | AWM monitoring requires strict referential integrity between registrants, series, funds, and holdings. Window functions (`ROW_NUMBER() OVER PARTITION`) are essential for concentration rankings. |
| **Full Ingestion Pathway** | Streaming binary `COPY FROM` | SQLAlchemy ORM `session.add_all()` | ORM object materialization for 6,025,567 holdings consumes $>8\text{ GB}$ RAM and requires hours. Binary `COPY` completed in 175 seconds with only 89 MB peak RAM. |
| **Risk Scoring Authority** | Deterministic Formula | Generative LLM Scoring | Financial regulators and auditors require explainable, repeatable scoring. LLMs suffer from non-deterministic variance and hallucinations. |
| **Exception Taxonomy** | 4-Tier Explicit Taxonomy | Binary Pass/Fail Flag | Single-quarter SEC files lack historical baselines, and some funds omit schedules. A binary pass/fail falsely categorizes missing filings as control breaches. |
| **AI Degradation Strategy** | Structured Template Fallback | Hard Error when No Key | Allows the platform to be fully functional out of the box in offline, air-gapped, or keyless evaluation environments without crashing. |
| **Audit Log Architecture** | Append-Only Table with JSON Diffs | In-Place `updated_at` timestamps | SOX / institutional audit readiness requires an indelible historical record of who changed what, when, and why. |

---

## 18. Assumptions, Known Limitations & Future Considerations

### 18.1 Current Assumptions & Boundaries
- **Public Data Frequency:** Operates on SEC Form N-PORT quarterly bulk releases. It does not reflect intraday position adjustments or real-time trading executions.
- **Reporting Period Granularity:** Holdings schedules are pegged to monthly/quarterly snapshot dates (`2025-06-30`, `2025-05-31`, `2025-07-31`).
- **SEC Filing Schedule Omissions:** A tiny fraction of funds ($3$ out of $6,600$ in 2025Q3) omit Part C security schedules in EDGAR. The platform correctly categorizes these as `DATA_AVAILABILITY`.

### 18.2 Known Technical Items
- **Pydantic v2 Migration Warnings:** In `backend/schemas/models.py`, two models use class-based `Config` rather than `ConfigDict`. This generates harmless deprecation warnings in Python 3.9/3.12 without affecting runtime functionality.
- **Single-Quarter Baseline Limitation:** In single-quarter ingestion, period-over-period controls (`REC-001`, `VAL-002`, `CLS-001`) evaluate as `NOT_TESTABLE` with 0 exceptions because no $T-1$ filings exist in the database.

### 18.3 Roadmap & Future Considerations
- **Multi-Quarter Ingestion Pipeline:** Automate the sequential downloading and ingestion of multiple historical quarters (e.g., 2024Q1 through 2025Q3) to activate full multi-period reconciliation across all funds.
- **Integration with Market Pricing Feeds:** Supplement SEC reported valuations with external daily end-of-day market pricing (e.g., Refinitiv or Bloomberg open APIs) to validate implied prices against secondary market quotes.
- **Automated SEC EDGAR RSS Webhook:** Monitor the SEC EDGAR RSS filing feed for live Form N-PORT-P and N-PORT-A (amendment) filings to trigger real-time micro-ingestion.

---

## 19. Operational Runbook & Troubleshooting

### 19.1 System Health Verification
To verify backend and database health via CLI:
```bash
PYTHONPATH=. python -c "
from backend.main import app
from fastapi.testclient import TestClient
client = TestClient(app)
print(client.get('/health').json())
"
```
**Expected Output:**
```json
{"status": "healthy", "version": "1.0.0", "database": {"status": "healthy", "tables": 20}, "ai_provider": "none"}
```

### 19.2 Database Connection Failures
- **Symptom:** `psycopg2.OperationalError: connection to server at "localhost", port 5432 failed`.
- **Diagnosis:** PostgreSQL service is stopped or port 5432 is occupied.
- **Resolution:**
  ```bash
  # Check PostgreSQL service status
  brew services list | grep postgresql  # macOS
  sudo systemctl status postgresql      # Linux
  
  # Restart service
  brew services restart postgresql@16
  ```

### 19.3 Re-Running Control Executions
If control executions need to be recalculated for a reporting period:
```bash
# Force re-run of all 16 controls
PYTHONPATH=. python scripts/run_controls.py --period 2025-06-30
```

### 19.4 Refreshing Metrics Snapshots
The `run_controls.py` script automatically triggers recalculation of all KRIs, KCIs, and KPIs upon completion. To inspect metric results directly in PostgreSQL:
```sql
SELECT kri_id, name, value, unit, status, trend 
FROM kri_snapshots 
WHERE period_date = '2025-06-30' 
ORDER BY kri_id;
```

---

*Document compiled and verified against current code implementation.*  
*Repository: [https://github.com/raghavkhetarpal/control-watch.git](https://github.com/raghavkhetarpal/control-watch.git)*  
*Status: **`READY FOR PORTFOLIO`***
