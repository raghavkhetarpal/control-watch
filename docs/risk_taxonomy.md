# Risk Taxonomy

*Disclaimer: These methodologies and thresholds are illustrative analytical thresholds for educational purposes only. They do not reflect the institutional risk framework of Goldman Sachs or any other financial institution.*

## Risk Categories
- **Data Quality**: Risks arising from inaccurate, incomplete, or malformed data.
- **Reconciliation**: Risks related to mismatches between discrete data points or systems.
- **Valuation**: Risks associated with incorrect or stale pricing of assets.
- **Concentration**: Risks of over-exposure to single entities, sectors, or asset classes.
- **Reporting**: Risks of failing to meet regulatory reporting deadlines or completeness.
- **Process**: Risks related to operational process failures.
- **Control Effectiveness**: Risks of controls failing to operate as designed.
- **Technology**: System or infrastructure failure risks.

## Severity Scale
- **LOW**: Minor impact, easily correctable, immaterial financial/regulatory consequence.
- **MEDIUM**: Moderate impact, requires investigation, potential for minor financial/reputational effect.
- **HIGH**: Significant impact, immediate remediation required, material financial or regulatory consequences.
- **CRITICAL**: Severe impact, systemic failure, major regulatory breach or financial loss.

## Likelihood Scale
1. **Rare**: Unlikely to occur (e.g., < once per year)
2. **Unlikely**: Not expected but possible (e.g., once per year)
3. **Possible**: Might occur at some time (e.g., quarterly)
4. **Likely**: Expected to occur in most circumstances (e.g., monthly)
5. **Almost Certain**: Expected to occur frequently (e.g., weekly/daily)

## Impact Scale
1. **Negligible**: No noticeable impact.
2. **Minor**: Small effort to remediate, no financial impact.
3. **Moderate**: Noticeable disruption, minor financial or regulatory impact.
4. **Major**: Significant disruption, material financial loss or regulatory attention.
5. **Severe**: Systemic failure, massive financial loss, severe regulatory penalty.

## Calculations

### Inherent Risk
`Inherent Risk = Impact * Likelihood`
Range: 1 to 25.

### Control Effectiveness
Assessed on a 1-5 scale:
1: Ineffective
2: Weak
3: Adequate
4: Strong
5: Very Strong

### Risk Scoring Formula
To factor in control effectiveness to derive the overall risk score:
`Risk Score = Impact * Likelihood * (6 - Control Effectiveness)`
*(The `(6 - CE)` term inverts effectiveness so stronger controls reduce the score)*
Range: 1 to 125.

## Scoring Thresholds
- **LOW**: 1 - 24
- **MEDIUM**: 25 - 49
- **HIGH**: 50 - 74
- **CRITICAL**: 75 - 125

## Worked Example
A valuation pricing feed failure (Valuation Risk).
- **Likelihood**: 3 (Possible)
- **Impact**: 4 (Major)
- **Inherent Risk**: 12
- **Control Effectiveness**: 2 (Weak manual checks)
- **Risk Score**: 3 * 4 * (6 - 2) = 12 * 4 = **48 (MEDIUM)**

If the control is improved to 4 (Strong automated checks):
- **Risk Score**: 3 * 4 * (6 - 4) = 12 * 2 = **24 (LOW)**
