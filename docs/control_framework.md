# Control Framework

This document outlines the controls implemented in the AWM ControlWatch system. 
*Note: All thresholds listed below are 'Illustrative analytical thresholds' for educational purposes.*

## Data Quality Controls
### DQ-001: Missing Mandatory Identifiers
- **Objective**: Identify records missing critical identifiers (e.g., CUSIP, LEI).
- **Risk Addressed**: Data Quality
- **Input**: Portfolio holdings data.
- **Logic**: Select records where identifier fields are NULL or blank.
- **Threshold**: Green: 0, Amber: 1-5%, Red: >5%
- **Output**: List of holdings missing identifiers.
- **Limitations**: Only checks for presence, not validity of the identifier.

### DQ-002: Invalid Identifier Format
- **Objective**: Ensure identifiers match expected patterns (e.g., 9-character CUSIP).
- **Risk Addressed**: Data Quality
- **Input**: Portfolio holdings identifiers.
- **Logic**: Regex or length validation on identifier strings.
- **Threshold**: Green: 0, Amber: 1-5%, Red: >5%
- **Output**: List of holdings with malformed identifiers.
- **Limitations**: Format validity does not guarantee the identifier exists in real-world systems.

### DQ-003: Negative Quantities for Long Positions
- **Objective**: Detect long positions incorrectly reported with negative quantities.
- **Risk Addressed**: Data Quality
- **Input**: Holdings quantity and position type.
- **Logic**: Select records where position_type = 'Long' and quantity < 0.
- **Threshold**: Green: 0, Amber: 1-5%, Red: >5%
- **Output**: List of holdings with negative long quantities.
- **Limitations**: Depends on accurate position_type flagging.

### DQ-004: Missing Asset Class Classification
- **Objective**: Identify holdings without a mapped asset class.
- **Risk Addressed**: Data Quality
- **Input**: Holdings asset class field.
- **Logic**: Select records where asset_class is NULL or 'Unknown'.
- **Threshold**: Green: <1%, Amber: 1-5%, Red: >5%
- **Output**: List of holdings missing asset class.
- **Limitations**: Cannot verify if a populated asset class is the correct one.

## Reconciliation Controls
### REC-001: Total Net Assets Mismatch
- **Objective**: Reconcile sum of position values to reported Total Net Assets.
- **Risk Addressed**: Reconciliation
- **Input**: Holdings values, Fund TNA.
- **Logic**: Sum(position_value) - Fund.TNA > tolerance.
- **Threshold**: Green: <0.1% diff, Amber: 0.1-1% diff, Red: >1% diff
- **Output**: Fund-level reconciliation break amount.
- **Limitations**: Does not account for uninvested cash or non-portfolio assets not in the dataset.

### REC-002: Outstanding Shares Mismatch
- **Objective**: Compare reported outstanding shares against derived shares.
- **Risk Addressed**: Reconciliation
- **Input**: Class-level share data.
- **Logic**: ABS(reported_shares - derived_shares) > tolerance.
- **Threshold**: Green: <0.1%, Amber: 0.1-1%, Red: >1%
- **Output**: Share class reconciliation breaks.
- **Limitations**: Derived shares may lack intra-period adjustments.

## Valuation Controls
### VAL-001: Stale Pricing Detection
- **Objective**: Identify positions with unchanged prices over multiple periods.
- **Risk Addressed**: Valuation
- **Input**: Historical pricing data.
- **Logic**: Compare current price to previous period price.
- **Threshold**: Green: 0, Amber: 1-5%, Red: >5%
- **Output**: List of stale priced assets.
- **Limitations**: Some illiquid assets naturally have unchanged prices.

### VAL-002: Extreme Price Variance
- **Objective**: Detect period-over-period price movements exceeding expected volatility.
- **Risk Addressed**: Valuation
- **Input**: Current and previous period prices.
- **Logic**: ABS((current_price / prev_price) - 1) > variance_threshold.
- **Threshold**: Green: <10%, Amber: 10-25%, Red: >25%
- **Output**: Assets with extreme price variance.
- **Limitations**: High volatility may be market-driven, not a valuation error.

## Concentration Controls
### CONC-001: Single Issuer Concentration
- **Objective**: Monitor exposure to a single issuer.
- **Risk Addressed**: Concentration
- **Input**: Holdings by issuer.
- **Logic**: SUM(value) by issuer / TNA.
- **Threshold**: Green: <5%, Amber: 5-10%, Red: >10%
- **Output**: Issuers exceeding concentration thresholds.
- **Limitations**: Illustrative threshold only; actual limits vary by mandate.

### CONC-002: Sector Concentration
- **Objective**: Monitor exposure to specific economic sectors.
- **Risk Addressed**: Concentration
- **Input**: Holdings by sector.
- **Logic**: SUM(value) by sector / TNA.
- **Threshold**: Green: <20%, Amber: 20-30%, Red: >30%
- **Output**: Sectors exceeding limits.
- **Limitations**: Depends on accurate sector mapping.

### CONC-003: Asset Class Concentration
- **Objective**: Monitor asset allocation limits.
- **Risk Addressed**: Concentration
- **Input**: Holdings by asset class.
- **Logic**: SUM(value) by asset class / TNA.
- **Threshold**: Green: within target, Amber: target +/- 5%, Red: target +/- 10%
- **Output**: Asset classes outside target allocation.
- **Limitations**: Simplified targets used for illustrative purposes.

### CONC-004: Geographic Concentration
- **Objective**: Monitor exposure to specific countries/regions.
- **Risk Addressed**: Concentration
- **Input**: Holdings by country.
- **Logic**: SUM(value) by country / TNA.
- **Threshold**: Green: <15%, Amber: 15-25%, Red: >25%
- **Output**: Countries exceeding exposure limits.
- **Limitations**: Relies on issuer country mapping, which may not reflect economic exposure.

## Liquidity Controls
### LIQ-001: Illiquid Asset Limit
- **Objective**: Monitor the percentage of highly illiquid assets in a fund.
- **Risk Addressed**: Liquidity
- **Input**: Asset liquidity classifications.
- **Logic**: SUM(illiquid_assets) / TNA.
- **Threshold**: Green: <5%, Amber: 5-15%, Red: >15%
- **Output**: Funds exceeding illiquid asset limits.
- **Limitations**: Uses proxy-based liquidity flags, not actual market volume or institutional models.

## Reporting Controls
### RPT-001: Late Filing Detection
- **Objective**: Identify filings submitted past the regulatory deadline.
- **Risk Addressed**: Reporting
- **Input**: Filing dates.
- **Logic**: filing_date > expected_deadline.
- **Threshold**: Green: 0 days late, Amber: 1-3 days late, Red: >3 days late
- **Output**: Late filed accession numbers.
- **Limitations**: Depends on static expected deadline assumptions.

### RPT-002: Missing Attachments
- **Objective**: Identify filings missing required XML/TSV attachments.
- **Risk Addressed**: Reporting
- **Input**: Filing metadata.
- **Logic**: check for presence of required attachments in filing package.
- **Threshold**: Green: None missing, Red: Any missing
- **Output**: Filings with missing attachments.
- **Limitations**: Only checks for file presence, not contents.

## Process Controls
### CLS-001: Unexpected Fund Closure
- **Objective**: Detect funds that drop out of filings without liquidation notice.
- **Risk Addressed**: Process
- **Input**: Fund lists across periods.
- **Logic**: Fund present in T-1, absent in T, with no closure flag.
- **Threshold**: Green: 0, Red: >0
- **Output**: List of unexpectedly missing funds.
- **Limitations**: Filings may simply be delayed rather than the fund being closed.
