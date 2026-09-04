-- AWM ControlWatch - PostgreSQL Schema
-- Educational/research implementation based on publicly available SEC data.
-- Does NOT replicate or represent Goldman Sachs' proprietary systems, controls, data, or risk framework.

-- ============================================================
-- INGESTION & SOURCE DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id SERIAL PRIMARY KEY,
    quarter VARCHAR(10) NOT NULL,
    download_url TEXT,
    file_hash VARCHAR(64),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL')),
    rows_processed INTEGER DEFAULT 0,
    rows_rejected INTEGER DEFAULT 0,
    files_extracted TEXT[],
    duration_seconds NUMERIC(10,2),
    error_message TEXT,
    is_sample BOOLEAN DEFAULT FALSE,
    sample_size INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ingestion_runs_quarter_hash
    ON ingestion_runs(quarter, file_hash) WHERE status = 'COMPLETED';

CREATE TABLE IF NOT EXISTS submissions (
    accession_number VARCHAR(25) PRIMARY KEY,
    filing_date DATE,
    period_of_report DATE,
    filing_type VARCHAR(20),
    is_amendment BOOLEAN DEFAULT FALSE,
    ingestion_run_id INTEGER REFERENCES ingestion_runs(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submissions_period ON submissions(period_of_report);
CREATE INDEX IF NOT EXISTS idx_submissions_filing_date ON submissions(filing_date);

CREATE TABLE IF NOT EXISTS registrants (
    cik VARCHAR(20) PRIMARY KEY,
    registrant_name TEXT NOT NULL,
    lei VARCHAR(20),
    street1 TEXT,
    city TEXT,
    state VARCHAR(10),
    country VARCHAR(10),
    zip VARCHAR(20),
    phone VARCHAR(30),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fund_series (
    series_id VARCHAR(20) PRIMARY KEY,
    cik VARCHAR(20) REFERENCES registrants(cik),
    series_name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fund_series_cik ON fund_series(cik);

CREATE TABLE IF NOT EXISTS funds (
    id SERIAL PRIMARY KEY,
    accession_number VARCHAR(25) NOT NULL REFERENCES submissions(accession_number) ON DELETE CASCADE,
    series_id VARCHAR(20) REFERENCES fund_series(series_id),
    cik VARCHAR(20) REFERENCES registrants(cik),
    fund_name TEXT,
    total_assets NUMERIC(20,2),
    net_assets NUMERIC(20,2),
    total_liabilities NUMERIC(20,2),
    period_of_report DATE,
    filing_date DATE,
    is_final_filing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(accession_number, series_id)
);

CREATE INDEX IF NOT EXISTS idx_funds_period ON funds(period_of_report);
CREATE INDEX IF NOT EXISTS idx_funds_series ON funds(series_id);
CREATE INDEX IF NOT EXISTS idx_funds_cik ON funds(cik);

CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    accession_number VARCHAR(25) NOT NULL REFERENCES submissions(accession_number) ON DELETE CASCADE,
    holding_id VARCHAR(50),
    fund_id INTEGER REFERENCES funds(id) ON DELETE CASCADE,
    -- Security identifiers
    name TEXT,
    title TEXT,
    cusip VARCHAR(9),
    isin VARCHAR(12),
    lei VARCHAR(20),
    ticker VARCHAR(20),
    other_id TEXT,
    other_id_desc TEXT,
    -- Position data
    balance NUMERIC(20,4),
    units VARCHAR(10),
    unit_desc TEXT,
    currency_code VARCHAR(3) DEFAULT 'USD',
    exchange_rate NUMERIC(16,8),
    value NUMERIC(20,2),
    pct_val NUMERIC(10,6),
    -- Classification
    asset_cat VARCHAR(10),
    asset_cat_desc TEXT,
    issuer_cat VARCHAR(10),
    issuer_cat_desc TEXT,
    investment_country VARCHAR(3),
    -- Debt-specific
    coupon_rate NUMERIC(10,6),
    maturity_date DATE,
    is_default BOOLEAN DEFAULT FALSE,
    are_interests_in_default BOOLEAN DEFAULT FALSE,
    -- Payoff profile
    payoff_profile VARCHAR(10),
    -- Liquidity classification
    fair_value_level VARCHAR(5),
    -- Metadata
    is_restricted BOOLEAN DEFAULT FALSE,
    is_loan_by_fund BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(accession_number, holding_id)
);

CREATE INDEX IF NOT EXISTS idx_holdings_accession ON holdings(accession_number);
CREATE INDEX IF NOT EXISTS idx_holdings_fund ON holdings(fund_id);
CREATE INDEX IF NOT EXISTS idx_holdings_cusip ON holdings(cusip);
CREATE INDEX IF NOT EXISTS idx_holdings_isin ON holdings(isin);
CREATE INDEX IF NOT EXISTS idx_holdings_asset_cat ON holdings(asset_cat);
CREATE INDEX IF NOT EXISTS idx_holdings_issuer_cat ON holdings(issuer_cat);
CREATE INDEX IF NOT EXISTS idx_holdings_country ON holdings(investment_country);
CREATE INDEX IF NOT EXISTS idx_holdings_name ON holdings(name);

CREATE TABLE IF NOT EXISTS reporting_periods (
    id SERIAL PRIMARY KEY,
    period_date DATE NOT NULL UNIQUE,
    quarter VARCHAR(10),
    fund_count INTEGER DEFAULT 0,
    holding_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- CONTROL FRAMEWORK
-- ============================================================

CREATE TABLE IF NOT EXISTS control_definitions (
    control_id VARCHAR(20) PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    risk_category VARCHAR(50) NOT NULL,
    control_type VARCHAR(30) NOT NULL DEFAULT 'DETECTIVE',
    frequency VARCHAR(20) DEFAULT 'ON_INGESTION',
    is_active BOOLEAN DEFAULT TRUE,
    thresholds JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS control_executions (
    id SERIAL PRIMARY KEY,
    control_id VARCHAR(20) NOT NULL REFERENCES control_definitions(control_id),
    period_date DATE,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL')),
    records_scanned INTEGER DEFAULT 0,
    exceptions_found INTEGER DEFAULT 0,
    pass_rate NUMERIC(5,2),
    duration_ms INTEGER,
    execution_metadata JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_control_exec_control ON control_executions(control_id);
CREATE INDEX IF NOT EXISTS idx_control_exec_period ON control_executions(period_date);
CREATE INDEX IF NOT EXISTS idx_control_exec_status ON control_executions(status);

CREATE TABLE IF NOT EXISTS control_exceptions (
    id SERIAL PRIMARY KEY,
    control_id VARCHAR(20) NOT NULL REFERENCES control_definitions(control_id),
    execution_id INTEGER REFERENCES control_executions(id),
    fund_id INTEGER REFERENCES funds(id),
    holding_id INTEGER REFERENCES holdings(id),
    -- Exception details
    severity VARCHAR(10) NOT NULL DEFAULT 'MEDIUM'
        CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(30) NOT NULL DEFAULT 'DETECTED'
        CHECK (status IN ('DETECTED', 'TRIAGED', 'ASSIGNED', 'INVESTIGATING',
                          'REMEDIATION_PLANNED', 'REMEDIATION_IN_PROGRESS',
                          'VALIDATION', 'CLOSED', 'ACCEPTED')),
    risk_category VARCHAR(50),
    description TEXT NOT NULL,
    evidence JSONB DEFAULT '{}',
    -- Risk scoring
    impact INTEGER CHECK (impact BETWEEN 1 AND 5),
    likelihood INTEGER CHECK (likelihood BETWEEN 1 AND 5),
    control_effectiveness INTEGER CHECK (control_effectiveness BETWEEN 1 AND 5),
    risk_score INTEGER,
    inherent_risk_score INTEGER,
    residual_risk_score INTEGER,
    risk_level VARCHAR(10)
        CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    -- Root cause
    root_cause_category VARCHAR(50)
        CHECK (root_cause_category IS NULL OR root_cause_category IN (
            'DATA_QUALITY', 'PROCESS_FAILURE', 'TECHNOLOGY_FAILURE',
            'REFERENCE_DATA', 'HUMAN_PROCESS_INPUT', 'EXTERNAL_EVENT', 'UNKNOWN'
        )),
    root_cause_description TEXT,
    -- Assignment
    assigned_to VARCHAR(100),
    assigned_at TIMESTAMP,
    -- Dates
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    due_date DATE,
    closed_at TIMESTAMP,
    -- Metadata
    period_date DATE,
    is_repeat BOOLEAN DEFAULT FALSE,
    previous_exception_id INTEGER REFERENCES control_exceptions(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exceptions_control ON control_exceptions(control_id);
CREATE INDEX IF NOT EXISTS idx_exceptions_fund ON control_exceptions(fund_id);
CREATE INDEX IF NOT EXISTS idx_exceptions_severity ON control_exceptions(severity);
CREATE INDEX IF NOT EXISTS idx_exceptions_status ON control_exceptions(status);
CREATE INDEX IF NOT EXISTS idx_exceptions_risk_level ON control_exceptions(risk_level);
CREATE INDEX IF NOT EXISTS idx_exceptions_period ON control_exceptions(period_date);
CREATE INDEX IF NOT EXISTS idx_exceptions_assigned ON control_exceptions(assigned_to);

-- ============================================================
-- RISK ASSESSMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    fund_id INTEGER REFERENCES funds(id),
    period_date DATE NOT NULL,
    risk_category VARCHAR(50),
    inherent_risk_score NUMERIC(5,2),
    inherent_risk_level VARCHAR(10),
    control_effectiveness_score NUMERIC(5,2),
    control_effectiveness_level VARCHAR(10),
    residual_risk_score NUMERIC(5,2),
    residual_risk_level VARCHAR(10),
    contributing_factors JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_assess_fund ON risk_assessments(fund_id);
CREATE INDEX IF NOT EXISTS idx_risk_assess_period ON risk_assessments(period_date);

-- ============================================================
-- KRI / KCI / KPI SNAPSHOTS
-- ============================================================

CREATE TABLE IF NOT EXISTS kri_snapshots (
    id SERIAL PRIMARY KEY,
    kri_id VARCHAR(20) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    period_date DATE NOT NULL,
    numerator NUMERIC(20,4),
    denominator NUMERIC(20,4),
    value NUMERIC(10,4) NOT NULL,
    unit VARCHAR(20) DEFAULT 'PERCENTAGE',
    threshold_green NUMERIC(10,4),
    threshold_amber NUMERIC(10,4),
    threshold_red NUMERIC(10,4),
    status VARCHAR(10) NOT NULL DEFAULT 'GREEN'
        CHECK (status IN ('GREEN', 'AMBER', 'RED')),
    trend VARCHAR(10) DEFAULT 'STABLE'
        CHECK (trend IN ('IMPROVING', 'STABLE', 'DETERIORATING')),
    previous_value NUMERIC(10,4),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(kri_id, period_date)
);

CREATE INDEX IF NOT EXISTS idx_kri_period ON kri_snapshots(period_date);
CREATE INDEX IF NOT EXISTS idx_kri_status ON kri_snapshots(status);

CREATE TABLE IF NOT EXISTS kci_snapshots (
    id SERIAL PRIMARY KEY,
    kci_id VARCHAR(20) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    period_date DATE NOT NULL,
    numerator NUMERIC(20,4),
    denominator NUMERIC(20,4),
    value NUMERIC(10,4) NOT NULL,
    unit VARCHAR(20) DEFAULT 'PERCENTAGE',
    threshold_green NUMERIC(10,4),
    threshold_amber NUMERIC(10,4),
    threshold_red NUMERIC(10,4),
    status VARCHAR(10) NOT NULL DEFAULT 'GREEN'
        CHECK (status IN ('GREEN', 'AMBER', 'RED')),
    trend VARCHAR(10) DEFAULT 'STABLE'
        CHECK (trend IN ('IMPROVING', 'STABLE', 'DETERIORATING')),
    previous_value NUMERIC(10,4),
    control_id VARCHAR(20) REFERENCES control_definitions(control_id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(kci_id, period_date)
);

CREATE INDEX IF NOT EXISTS idx_kci_period ON kci_snapshots(period_date);

CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id SERIAL PRIMARY KEY,
    kpi_id VARCHAR(20) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    period_date DATE NOT NULL,
    value NUMERIC(20,4) NOT NULL,
    unit VARCHAR(20) DEFAULT 'COUNT',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(kpi_id, period_date)
);

CREATE INDEX IF NOT EXISTS idx_kpi_period ON kpi_snapshots(period_date);

-- ============================================================
-- REMEDIATION & WORKFLOW
-- ============================================================

CREATE TABLE IF NOT EXISTS remediation_items (
    id SERIAL PRIMARY KEY,
    exception_id INTEGER NOT NULL REFERENCES control_exceptions(id) ON DELETE CASCADE,
    owner VARCHAR(100),
    action_description TEXT NOT NULL,
    due_date DATE,
    priority VARCHAR(10) DEFAULT 'MEDIUM'
        CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'VALIDATED', 'OVERDUE', 'CANCELLED')),
    validation_result TEXT,
    validated_at TIMESTAMP,
    validated_by VARCHAR(100),
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_remediation_exception ON remediation_items(exception_id);
CREATE INDEX IF NOT EXISTS idx_remediation_status ON remediation_items(status);
CREATE INDEX IF NOT EXISTS idx_remediation_owner ON remediation_items(owner);
CREATE INDEX IF NOT EXISTS idx_remediation_due_date ON remediation_items(due_date);

-- ============================================================
-- AUDIT TRAIL
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    actor VARCHAR(100) NOT NULL DEFAULT 'SYSTEM',
    action VARCHAR(50) NOT NULL,
    object_type VARCHAR(50) NOT NULL,
    object_id TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_object ON audit_events(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action);

-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    email VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'ANALYST'
        CHECK (role IN ('ADMIN', 'MANAGER', 'ANALYST', 'VIEWER', 'SYSTEM')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- System user for automated actions
INSERT INTO users (username, display_name, role) VALUES ('system', 'System', 'SYSTEM')
ON CONFLICT (username) DO NOTHING;

-- ============================================================
-- AI ANALYSIS
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_analysis (
    id SERIAL PRIMARY KEY,
    analysis_type VARCHAR(50) NOT NULL,
    query TEXT NOT NULL,
    context_summary TEXT,
    evidence_hash VARCHAR(64),
    evidence JSONB NOT NULL DEFAULT '{}',
    response TEXT NOT NULL,
    provider VARCHAR(20),
    model VARCHAR(50),
    -- Validation
    validation_status VARCHAR(20) DEFAULT 'PENDING'
        CHECK (validation_status IN ('PENDING', 'VALIDATED', 'FLAGGED', 'REJECTED')),
    validation_issues JSONB DEFAULT '[]',
    -- Metadata
    tokens_used INTEGER,
    latency_ms INTEGER,
    requested_by VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_type ON ai_analysis(analysis_type);
CREATE INDEX IF NOT EXISTS idx_ai_validation ON ai_analysis(validation_status);

-- ============================================================
-- DATA QUALITY RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS data_quality_results (
    id SERIAL PRIMARY KEY,
    ingestion_run_id INTEGER REFERENCES ingestion_runs(id),
    period_date DATE,
    total_records INTEGER NOT NULL,
    clean_records INTEGER NOT NULL,
    rejected_records INTEGER NOT NULL,
    quality_score NUMERIC(5,2),
    issues JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- REFERENCE DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS reference_data (
    id SERIAL PRIMARY KEY,
    ref_type VARCHAR(30) NOT NULL,
    code VARCHAR(20) NOT NULL,
    label TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(ref_type, code)
);

-- Seed reference data for asset categories
INSERT INTO reference_data (ref_type, code, label, description) VALUES
    ('ASSET_CAT', 'EC', 'Equity - Common', 'Common stock equity'),
    ('ASSET_CAT', 'EP', 'Equity - Preferred', 'Preferred stock equity'),
    ('ASSET_CAT', 'DBT', 'Debt', 'Debt instruments'),
    ('ASSET_CAT', 'ABS', 'Asset-Backed Securities', 'Asset-backed securities'),
    ('ASSET_CAT', 'STIV', 'Short-Term Investments', 'Short-term investment vehicles'),
    ('ASSET_CAT', 'MF', 'Mutual Fund', 'Mutual fund shares'),
    ('ASSET_CAT', 'OTHER', 'Other', 'Other asset categories'),
    ('ISSUER_CAT', 'CORP', 'Corporate', 'Corporate issuer'),
    ('ISSUER_CAT', 'USG', 'U.S. Government', 'U.S. Government'),
    ('ISSUER_CAT', 'USGA', 'U.S. Govt Agency', 'U.S. Government Agency'),
    ('ISSUER_CAT', 'MUN', 'Municipal', 'Municipal issuer'),
    ('ISSUER_CAT', 'FGN', 'Foreign Government', 'Foreign Government'),
    ('ISSUER_CAT', 'OTHER', 'Other', 'Other issuer category'),
    ('ROOT_CAUSE', 'DATA_QUALITY', 'Data Quality', 'Issue with source data quality'),
    ('ROOT_CAUSE', 'PROCESS_FAILURE', 'Process Failure', 'Operational process failure'),
    ('ROOT_CAUSE', 'TECHNOLOGY_FAILURE', 'Technology Failure', 'System or technology failure'),
    ('ROOT_CAUSE', 'REFERENCE_DATA', 'Reference Data', 'Reference data issue'),
    ('ROOT_CAUSE', 'HUMAN_PROCESS_INPUT', 'Human/Process Input', 'Human input error'),
    ('ROOT_CAUSE', 'EXTERNAL_EVENT', 'External Event', 'External market or event'),
    ('ROOT_CAUSE', 'UNKNOWN', 'Unknown', 'Root cause not yet determined')
ON CONFLICT (ref_type, code) DO NOTHING;

-- Seed control definitions
INSERT INTO control_definitions (control_id, name, description, risk_category, control_type, thresholds) VALUES
    ('DQ-001', 'Missing Required Fields', 'Detect missing critical fields in holdings data', 'DATA_QUALITY', 'DETECTIVE', '{"amber_pct": 1.0, "red_pct": 5.0}'),
    ('DQ-002', 'Duplicate Holdings', 'Detect duplicate holdings based on natural keys', 'DATA_QUALITY', 'DETECTIVE', '{"amber_count": 10, "red_count": 50}'),
    ('DQ-003', 'Invalid Values', 'Detect invalid or impossible values in holdings data', 'DATA_QUALITY', 'DETECTIVE', '{"amber_pct": 2.0, "red_pct": 10.0}'),
    ('DQ-004', 'Classification Consistency', 'Check consistency of security classifications', 'DATA_QUALITY', 'DETECTIVE', '{"amber_pct": 5.0, "red_pct": 15.0}'),
    ('REC-001', 'Period-over-Period Reconciliation', 'Compare holdings between consecutive reporting periods', 'RECONCILIATION', 'DETECTIVE', '{"value_change_pct": 50.0, "quantity_change_pct": 50.0}'),
    ('REC-002', 'Portfolio Completeness', 'Verify portfolio value completeness against fund totals', 'RECONCILIATION', 'DETECTIVE', '{"tolerance_pct": 5.0}'),
    ('VAL-001', 'Stale/Zero Prices', 'Detect holdings with stale or zero implied prices', 'VALUATION', 'DETECTIVE', '{"stale_periods": 2}'),
    ('VAL-002', 'Extreme Price Movements', 'Detect unusually large price changes period-over-period', 'VALUATION', 'DETECTIVE', '{"change_threshold_pct": 50.0}'),
    ('CONC-001', 'Position Concentration', 'Calculate top position concentration per fund', 'CONCENTRATION', 'DETECTIVE', '{"green_pct": 35.0, "amber_pct": 45.0}'),
    ('CONC-002', 'Issuer Concentration', 'Calculate issuer-level concentration', 'CONCENTRATION', 'DETECTIVE', '{"green_pct": 25.0, "amber_pct": 35.0}'),
    ('CONC-003', 'Asset Class Concentration', 'Calculate asset class concentration', 'CONCENTRATION', 'DETECTIVE', '{"green_pct": 60.0, "amber_pct": 80.0}'),
    ('CONC-004', 'Geographic Concentration', 'Calculate geographic concentration', 'CONCENTRATION', 'DETECTIVE', '{"green_pct": 70.0, "amber_pct": 85.0}'),
    ('LIQ-001', 'Liquidity Proxy', 'Analytical liquidity-risk indicator based on asset classification', 'LIQUIDITY', 'DETECTIVE', '{"illiquid_amber_pct": 15.0, "illiquid_red_pct": 25.0}'),
    ('RPT-001', 'Reporting Timeliness', 'Monitor filing timeliness relative to reporting period', 'REPORTING', 'DETECTIVE', '{"amber_days": 60, "red_days": 90}'),
    ('RPT-002', 'Reporting Gaps', 'Detect missing reporting periods for fund series', 'REPORTING', 'DETECTIVE', '{}'),
    ('CLS-001', 'Classification Changes', 'Detect period-over-period classification reclassifications', 'DATA_QUALITY', 'DETECTIVE', '{}')
ON CONFLICT (control_id) DO NOTHING;
