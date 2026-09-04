"""Data Normalizer for SEC Form N-PORT TSV data."""
import re
from typing import Optional
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

# Standard SEC asset category mappings
ASSET_CAT_MAP = {
    "EC": "EC",          # Equity-Common
    "EP": "EP",          # Equity-Preferred
    "DBT": "DBT",        # Debt
    "DBT-CORP": "DBT",   # Debt - Corporate
    "DBT-MUNI": "DBT",   # Debt - Municipal
    "DBT-USG": "DBT",    # Debt - US Government
    "ABS": "ABS",        # Asset-Backed
    "ABS-MBS": "ABS",    # Mortgage-Backed
    "STIV": "STIV",      # Short-Term Investment Vehicle
    "MF": "MF",          # Mutual Fund
    "OTHER": "OTHER",
    "DE": "DE",          # Derivative
    "FND": "FND",        # Fund
}

# Standard SEC issuer category mappings
ISSUER_TYPE_MAP = {
    "CORP": "CORP",
    "USG": "USG",
    "USGA": "USGA",
    "MUN": "MUN",
    "FGN": "FGN",
    "OTHER": "OTHER",
}


def clean_date_column(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """Safely convert strings to date objects."""
    if col_name in df.columns:
        df[col_name] = pd.to_datetime(df[col_name], errors='coerce').dt.date
    return df


def clean_numeric_column(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """Safely convert strings to float numeric."""
    if col_name in df.columns:
        df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
    return df


def normalize_cusip(cusip: Optional[str]) -> Optional[str]:
    """Validate and clean CUSIP (9 alphanumeric characters)."""
    if pd.isna(cusip) or not cusip:
        return None
    cleaned = re.sub(r'[^A-Za-z0-9]', '', str(cusip)).upper()
    return cleaned if len(cleaned) == 9 else None


def normalize_isin(isin: Optional[str]) -> Optional[str]:
    """Validate and clean ISIN (12 alphanumeric characters)."""
    if pd.isna(isin) or not isin:
        return None
    cleaned = re.sub(r'[^A-Za-z0-9]', '', str(isin)).upper()
    return cleaned if len(cleaned) == 12 else None


class DataNormalizer:

    @staticmethod
    def normalize_submission(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize raw SUBMISSION.tsv dataframe."""
        df = df.copy()
        # SEC column name mappings: REPORT_DATE -> period_of_report
        if 'report_date' in df.columns and 'period_of_report' not in df.columns:
            df['period_of_report'] = df['report_date']
        if 'report_ending_period' in df.columns and 'period_of_report' not in df.columns:
            df['period_of_report'] = df['report_ending_period']

        df = clean_date_column(df, 'filing_date')
        df = clean_date_column(df, 'period_of_report')

        if 'sub_type' in df.columns and 'filing_type' not in df.columns:
            df['filing_type'] = df['sub_type']

        if 'is_amendment' in df.columns:
            df['is_amendment'] = df['is_amendment'].fillna('N').map(
                {'Y': True, 'N': False, '1': True, '0': False, True: True, False: False}
            ).fillna(False)
        else:
            df['is_amendment'] = False

        return df

    @staticmethod
    def normalize_fund_info(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize raw FUND_REPORTED_INFO.tsv dataframe."""
        df = df.copy()
        numeric_cols = ['total_assets', 'net_assets', 'total_liabilities']
        for col in numeric_cols:
            df = clean_numeric_column(df, col)

        df = clean_date_column(df, 'period_of_report')
        df = clean_date_column(df, 'filing_date')

        if 'series_name' in df.columns and 'fund_name' not in df.columns:
            df['fund_name'] = df['series_name']

        return df

    @staticmethod
    def normalize_holding(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize raw FUND_REPORTED_HOLDING.tsv dataframe."""
        df = df.copy()

        # Map SEC column aliases to database columns
        col_mappings = {
            'issuer_name': 'name',
            'issuer_title': 'title',
            'issuer_cusip': 'cusip',
            'issuer_lei': 'lei',
            'unit': 'units',
            'currency_value': 'value',
            'percentage': 'pct_val',
            'issuer_type': 'issuer_cat',
            'is_restricted_security': 'is_restricted',
        }
        for sec_col, db_col in col_mappings.items():
            if sec_col in df.columns and db_col not in df.columns:
                df[db_col] = df[sec_col]

        # Numeric conversions
        numeric_cols = ['balance', 'value', 'pct_val', 'coupon_rate', 'exchange_rate']
        for col in numeric_cols:
            df = clean_numeric_column(df, col)

        df = clean_date_column(df, 'maturity_date')

        # Identifier normalizations
        if 'cusip' in df.columns:
            df['cusip'] = df['cusip'].apply(normalize_cusip)
        if 'isin' in df.columns:
            df['isin'] = df['isin'].apply(normalize_isin)

        # Asset category mapping
        if 'asset_cat' in df.columns:
            df['asset_cat'] = df['asset_cat'].astype(str).str.upper().apply(
                lambda x: ASSET_CAT_MAP.get(x, x[:10] if x != 'NAN' else None)
            )

        # Issuer category mapping
        if 'issuer_cat' in df.columns:
            df['issuer_cat'] = df['issuer_cat'].astype(str).str.upper().apply(
                lambda x: ISSUER_TYPE_MAP.get(x, x[:10] if x != 'NAN' else None)
            )

        # Booleans
        if 'is_restricted' in df.columns:
            df['is_restricted'] = df['is_restricted'].fillna('N').map(
                {'Y': True, 'N': False, '1': True, '0': False, True: True, False: False}
            ).fillna(False)

        # Deduplicate on natural keys (accession_number + holding_id)
        if 'accession_number' in df.columns and 'holding_id' in df.columns:
            df = df.drop_duplicates(subset=['accession_number', 'holding_id'])

        return df

    @staticmethod
    def normalize_registrant(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize raw REGISTRANT.tsv dataframe."""
        df = df.copy()
        if 'lei' in df.columns:
            df['lei'] = df['lei'].str.strip().str.upper()
        if 'cik' in df.columns:
            df['cik'] = df['cik'].astype(str).str.strip().str.zfill(10)
        return df

    @staticmethod
    def normalize_series(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize SERIES.tsv dataframe if present."""
        return df.copy()
