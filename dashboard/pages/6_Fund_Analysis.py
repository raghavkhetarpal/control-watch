import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Fund Deep Dive")

fund = st.selectbox("Select Fund", ["Fund A (Equity Growth)", "Fund B (Fixed Income)", "Fund C (Global Macro)"])

st.markdown(f"### Portfolio Composition: {fund}")
col1, col2 = st.columns(2)

with col1:
    assets = pd.DataFrame({"Asset Class": ["Equity", "Bonds", "Cash", "Derivatives"], "Allocation": [60, 25, 10, 5]})
    fig1 = px.pie(assets, values="Allocation", names="Asset Class", title="Asset Allocation")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    geo = pd.DataFrame({"Region": ["North America", "Europe", "Asia", "Emerging"], "Allocation": [50, 20, 20, 10]})
    fig2 = px.bar(geo, x="Region", y="Allocation", title="Geographic Exposure")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("### Top Holdings (Top 20 by Value)")
holdings = pd.DataFrame({
    "Issuer": ["Apple Inc", "Microsoft", "US Treasury", "Amazon", "Alphabet"],
    "Weight (%)": [5.2, 4.8, 4.0, 3.5, 3.2],
    "Value (USD)": ["$52M", "$48M", "$40M", "$35M", "$32M"]
})
st.dataframe(holdings, use_container_width=True)

st.markdown("### Concentration Metrics")
c1, c2, c3 = st.columns(3)
c1.metric("Top 1 Position", "5.2%")
c2.metric("Top 5 Positions", "20.7%")
c3.metric("Top 10 Positions", "35.1%")

st.markdown("### Fund-Specific Exceptions")
st.info("No critical exceptions for this fund.")
