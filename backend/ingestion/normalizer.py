import pandas as pd
import structlog
from typing import Dict

logger = structlog.get_logger(__name__)

ASSET_CAT_MAP = {
    "EC": "Equity-Common",
    "EP": "Equity-Preferred",
    "DB": "Debt-Corporate",
    "DG": "Debt-Government",
    "ST": "Short-Term",
    "OT": "Other"
    # This is an illustrative analytical mapping
}

def clean_date_column(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    if col_name in df.columns:
        df[col_name] = pd.to_datetime(df[col_name], errors='coerce').dt.date
    return df

def clean_numeric_column(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    if col_name in df.columns:
        df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
    return df

def normalize_cusip(cusip: str) -> str:
    if pd.isna(cusip):
        return None
    cusip = str(cusip).strip().upper()
    return cusip if len(cusip) == 9 else None

def normalize_isin(isin: str) -> str:
    if pd.isna(isin):
        return None
    isin = str(isin).strip().upper()
    return isin if len(isin) == 12 else None

class DataNormalizer:
    
    @staticmethod
    def normalize_submission(df: pd.DataFrame) -> pd.DataFrame:
        df = clean_date_column(df, 'filing_date')
        df = clean_date_column(df, 'period_of_report')
        if 'is_amendment' in df.columns:
            df['is_amendment'] = df['is_amendment'].fillna('N').map({'Y': True, 'N': False, '1': True, '0': False})
        return df
        
    @staticmethod
    def normalize_fund_info(df: pd.DataFrame) -> pd.DataFrame:
        numeric_cols = ['total_assets', 'net_assets', 'total_liabilities']
        for col in numeric_cols:
            df = clean_numeric_column(df, col)
        df = clean_date_column(df, 'period_of_report')
        df = clean_date_column(df, 'filing_date')
        return df
        
    @staticmethod
    def normalize_holding(df: pd.DataFrame) -> pd.DataFrame:
        numeric_cols = ['balance', 'value', 'pct_val', 'coupon_rate', 'exchange_rate', 'units']
        for col in numeric_cols:
            df = clean_numeric_column(df, col)
            
        df = clean_date_column(df, 'maturity_date')
        
        if 'cusip' in df.columns:
            df['cusip'] = df['cusip'].apply(normalize_cusip)
        if 'isin' in df.columns:
            df['isin'] = df['isin'].apply(normalize_isin)
            
        if 'asset_cat' in df.columns:
            # Derived field based on SEC code mapping
            df['asset_cat'] = df['asset_cat'].map(lambda x: ASSET_CAT_MAP.get(str(x).upper(), "Unknown/Derived"))
            
        boolean_cols = ['is_default', 'is_restricted']
        for col in boolean_cols:
            if col in df.columns:
                df[col] = df[col].fillna('N').map({'Y': True, 'N': False})
                
        # Deduplicate on natural keys (accession_number + holding_id) if both present
        if 'accession_number' in df.columns and 'holding_id' in df.columns:
            df = df.drop_duplicates(subset=['accession_number', 'holding_id'])
            
        return df

    @staticmethod
    def normalize_registrant(df: pd.DataFrame) -> pd.DataFrame:
        if 'lei' in df.columns:
            df['lei'] = df['lei'].str.strip().str.upper()
        return df

    @staticmethod
    def normalize_series(df: pd.DataFrame) -> pd.DataFrame:
        return df
