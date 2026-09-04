# Metrics Methodology: KRI, KCI, KPI

*Disclaimer: All thresholds listed below are illustrative analytical thresholds for educational purposes.*

## Definitions
- **KPI (Key Performance Indicator)**: Measures operational efficiency and processing performance.
- **KRI (Key Risk Indicator)**: Measures exposure to specific risks and potential for future adverse events.
- **KCI (Key Control Indicator)**: Measures the health, execution rate, and failure rate of the control environment itself.

## Data Lineage
- **Metrics Calculation**: Calculated by aggregating raw control execution data, exception logs, and system telemetry from the PostgreSQL database.
- **Trends**: Determined by comparing the current metric snapshot to the immediately preceding snapshot (e.g., current month vs. previous month).

## Key Risk Indicators (KRIs)

| ID | Name | Definition | Formula | Unit | Thresholds |
|---|---|---|---|---|---|
| KRI-01 | Total Exceptions | Total number of unmediated exceptions | Count(exceptions WHERE status != 'Closed') | Count | G:<100, A:100-500, R:>500 |
| KRI-02 | High Severity Exceptions | Number of High/Critical exceptions | Count(exceptions WHERE severity IN ('HIGH', 'CRITICAL')) | Count | G:0, A:1-10, R:>10 |
| KRI-03 | Avg Exception Age | Average days exceptions remain open | Avg(current_date - created_date) for open exceptions | Days | G:<5, A:5-15, R:>15 |
| KRI-04 | Concentration Risk Breaches | Funds exceeding concentration limits | Count(funds failing CONC controls) / Total funds | % | G:<2%, A:2-5%, R:>5% |
| KRI-05 | Valuation Breaches | Holdings with valuation anomalies | Count(holdings failing VAL controls) / Total holdings | % | G:<1%, A:1-3%, R:>3% |
| KRI-06 | Liquidity Breaches | Funds exceeding illiquid limits | Count(funds failing LIQ controls) / Total funds | % | G:<1%, A:1-5%, R:>5% |
| KRI-07 | Recon Break Value | Total value of reconciliation breaks | Sum(break_amount) | USD | G:<$1M, A:$1M-$10M, R:>$10M |

## Key Control Indicators (KCIs)

| ID | Name | Definition | Formula | Unit | Thresholds |
|---|---|---|---|---|---|
| KCI-01 | Control Execution Rate | % of scheduled controls executed | Count(executed controls) / Count(scheduled controls) | % | G:100%, A:95-99%, R:<95% |
| KCI-02 | Control Failure Rate | % of controls resulting in error | Count(failed controls) / Count(executed controls) | % | G:0%, A:0-2%, R:>2% |
| KCI-03 | False Positive Rate | % of exceptions closed as false positive | Count(exceptions closed as 'False Positive') / Count(closed exceptions) | % | G:<10%, A:10-25%, R:>25% |
| KCI-04 | Automated Control Coverage | % of controls fully automated | Count(automated controls) / Total controls | % | G:>90%, A:75-90%, R:<75% |
| KCI-05 | Control Effectiveness Score | Avg effectiveness score of controls | Avg(control_effectiveness_score) | Score (1-5) | G:>4, A:3-4, R:<3 |
| KCI-06 | Data Quality Pass Rate | % of records passing DQ controls | Count(records passing DQ) / Total records | % | G:>99%, A:95-99%, R:<95% |
| KCI-07 | Stale Controls | Controls not reviewed in >1 year | Count(controls with last_review > 1yr) | Count | G:0, A:1-5, R:>5 |

## Key Performance Indicators (KPIs)

| ID | Name | Definition | Formula | Unit | Thresholds |
|---|---|---|---|---|---|
| KPI-01 | Ingestion Time | Time to ingest SEC bulk data | Avg(ingestion_end - ingestion_start) | Minutes | G:<30, A:30-60, R:>60 |
| KPI-02 | Processing Volume | Total records processed per batch | Count(records) | Count | N/A (Volume indicator) |
| KPI-03 | Exception Resolution Time | Avg time to close an exception | Avg(resolved_date - created_date) | Days | G:<2, A:2-5, R:>5 |
| KPI-04 | System Uptime | % time system is available | (Total time - Downtime) / Total time | % | G:>99.9%, A:99-99.9%, R:<99% |
| KPI-05 | API Response Time | Avg latency of API requests | Avg(api_response_time) | ms | G:<200, A:200-500, R:>500 |
| KPI-06 | AI Copilot Response Time | Avg time for AI generation | Avg(ai_generation_time) | Seconds | G:<5, A:5-15, R:>15 |
| KPI-07 | Manual Adjustments | Number of manual data overrides | Count(manual_overrides) | Count | G:<10, A:10-50, R:>50 |
| KPI-08 | Dashboard Active Users | Daily active users on dashboard | Count(distinct user_id) per day | Count | N/A (Usage indicator) |
