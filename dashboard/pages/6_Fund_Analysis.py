import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db

st.title("🔍 Fund Deep Dive & Holdings Breakdown")
st.caption("Drill down into individual fund holdings reported in SEC Form N-PORT filings.")

# 1. Select Fund with holdings
@st.cache_data(ttl=30)
def load_funds_with_holdings():
    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT f.id, f.fund_name, COUNT(h.id) as holdings_count,
                   SUM(h.value) as total_holding_val, f.total_assets
            FROM funds f
            JOIN holdings h ON f.id = h.fund_id
            GROUP BY f.id, f.fund_name, f.total_assets
            HAVING COUNT(h.id) > 0
            ORDER BY holdings_count DESC
            LIMIT 50
        """)).mappings().all()
    return rows

fund_list = load_funds_with_holdings()

if fund_list:
    fund_options = {f"{f['fund_name']} ({f['holdings_count']} holdings)": f["id"] for f in fund_list}
    selected_label = st.selectbox("Select Fund Portfolio:", list(fund_options.keys()))
    selected_fund_id = fund_options[selected_label]
    fund_info = next(f for f in fund_list if f["id"] == selected_fund_id)

    # Fund Summary Cards
    col1, col2, col3 = st.columns(3)
    col1.metric("Holdings Ingested", f"{fund_info['holdings_count']:,}")
    tot_val = float(fund_info["total_holding_val"] or 0)
    col2.metric("Calculated Holdings Total", f"${tot_val:,.2f}")
    rep_val = float(fund_info["total_assets"] or 0)
    col3.metric("Reported Net Assets", f"${rep_val:,.2f}" if rep_val > 0 else "N/A")

    st.markdown("---")

    # Load Holdings
    @st.cache_data(ttl=30)
    def load_fund_holdings(fid):
        with get_engine().connect() as conn:
            h_rows = conn.execute(
                text("""
                    SELECT name, cusip, isin, value, pct_val, asset_cat, issuer_cat, investment_country
                    FROM holdings
                    WHERE fund_id = :fid
                    ORDER BY pct_val DESC NULLS LAST, value DESC NULLS LAST
                """),
                {"fid": fid}
            ).mappings().all()
            exc_rows = conn.execute(
                text("""
                    SELECT id, control_id, severity, description, status
                    FROM control_exceptions
                    WHERE fund_id = :fid
                    ORDER BY id DESC
                """),
                {"fid": fid}
            ).mappings().all()
        return h_rows, exc_rows

    holdings, excs = load_fund_holdings(selected_fund_id)

    if holdings:
        df_h = pd.DataFrame([dict(h) for h in holdings])

        # Concentration metrics
        c1, c2, c3 = st.columns(3)
        top1 = float(df_h.iloc[0]["pct_val"] or 0) if len(df_h) > 0 else 0
        top5 = float(df_h.iloc[:5]["pct_val"].sum() or 0) if len(df_h) > 0 else 0
        top10 = float(df_h.iloc[:10]["pct_val"].sum() or 0) if len(df_h) > 0 else 0
        c1.metric("Top 1 Position", f"{top1:.2f}%")
        c2.metric("Top 5 Positions", f"{top5:.2f}%")
        c3.metric("Top 10 Positions", f"{top10:.2f}%")

        # Composition Charts
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cat_agg = df_h.groupby("asset_cat")["value"].sum().reset_index()
            fig_pie = px.pie(cat_agg, values="value", names="asset_cat", title="Portfolio Asset Allocation", hole=0.3)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_c2:
            country_agg = df_h.groupby("investment_country")["value"].sum().reset_index()
            fig_bar = px.bar(country_agg, x="investment_country", y="value", title="Geographic Exposure by Country")
            st.plotly_chart(fig_bar, use_container_width=True)

        # Top Holdings Table
        st.markdown("### Top Holdings (Ranked by Portfolio Weight)")
        df_h["Value ($)"] = df_h["value"].apply(lambda v: f"${float(v or 0):,.2f}")
        df_h["Weight (%)"] = df_h["pct_val"].apply(lambda p: f"{float(p or 0):.2f}%")
        st.dataframe(
            df_h[["name", "cusip", "asset_cat", "investment_country", "Value ($)", "Weight (%)"]],
            column_config={
                "name": "Holding / Issuer Name",
                "cusip": "CUSIP",
                "asset_cat": "Asset Category",
                "investment_country": "Country",
                "Value ($)": "Position Value",
                "Weight (%)": "Portfolio Weight"
            },
            use_container_width=True,
            hide_index=True
        )

    # Fund Exceptions
    st.markdown("### Fund-Specific Control Exceptions")
    if excs:
        df_e = pd.DataFrame([dict(e) for e in excs])
        st.dataframe(
            df_e[["id", "control_id", "severity", "status", "description"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("No control exceptions detected for this fund portfolio.")

else:
    st.info("No funds with holdings available in database.")
