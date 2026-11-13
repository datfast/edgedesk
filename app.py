import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import json
from pathlib import Path

DATA_DIR = Path("edgedesk_data")
DATA_DIR.mkdir(exist_ok=True)

INDICES = ["SPY", "QQQ", "IWM"]
VIX = "^VIX"
KEY_STOCKS = ["NVDA", "TSLA", "AMD", "AAPL"]
ALL_TICKERS = INDICES + [VIX] + KEY_STOCKS

st.set_page_config(
    page_title="EdgeDesk",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    color: #1e293b;
}
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}
</style>
""", unsafe_allow_html=True)

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def load_session():
    path = DATA_DIR / f"session_{today_str()}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        "date": today_str(),
        "market_bias": "Neutral",
        "levels": {},
        "trade_plans": [],
        "notes": ""
    }

def save_session(session):
    path = DATA_DIR / f"session_{today_str()}.json"
    with open(path, "w") as f:
        json.dump(session, f, indent=2)

def fetch_market_data():
    results = {}
    for t in ALL_TICKERS:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if not hist.empty:
                results[t] = hist
        except Exception:
            continue
    return results

def compute_snapshot(data):
    snap = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "indices": {},
        "vix": None,
        "stocks": {},
        "suggested_bias": "Neutral",
        "notes": [],
    }
    for t in INDICES:
        if t not in data or data[t].empty:
            continue
        df = data[t]
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        change_pct = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100
        snap["indices"][t] = {
            "last": round(float(last["Close"]), 2),
            "change_pct": round(float(change_pct), 2)
        }
    if VIX in data and not data[VIX].empty:
        snap["vix"] = round(float(data[VIX].iloc[-1]["Close"]), 2)
    for t in KEY_STOCKS:
        if t not in data or data[t].empty:
            continue
        df = data[t]
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        change_pct = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100
        vol = last.get("Volume", 0)
        avg_vol = df["Volume"].tail(5).mean() if "Volume" in df else 1
        rvol = float(vol / avg_vol) if avg_vol > 0 else 1
        snap["stocks"][t] = {
            "last": round(float(last["Close"]), 2),
            "change_pct": round(float(change_pct), 2),
            "rvol": round(rvol, 2)
        }
    spy_chg = snap["indices"].get("SPY", {}).get("change_pct", 0)
    qqq_chg = snap["indices"].get("QQQ", {}).get("change_pct", 0)
    vix = snap.get("vix") or 20
    if spy_chg > 0.4 and qqq_chg > 0.4 and vix < 22:
        snap["suggested_bias"] = "Bullish"
    elif spy_chg < -0.4 and qqq_chg < -0.4:
        snap["suggested_bias"] = "Bearish"
    else:
        snap["suggested_bias"] = "Neutral"
    return snap

def render_snapshot(snap):
    st.caption(f"As of {snap.get('timestamp', '-')}")
    cols = st.columns(4)
    for i, t in enumerate(INDICES):
        info = snap.get("indices", {}).get(t)
        if info:
            cols[i].metric(t, f"{info.get('last', 0):.2f}", f"{info.get('change_pct', 0):+.2f}%")
    if snap.get("vix") is not None:
        cols[3].metric("VIX", f"{snap['vix']:.2f}")
    st.markdown(f"**Suggested Bias:** {snap.get('suggested_bias', 'Neutral')}")

def page_pre_market(session):
    st.header("Pre-Market / Live Market Scan")
    st.write("Live data for indices, VIX and key stocks")
    if st.button("Refresh Market Data"):
        st.cache_data.clear()
        st.rerun()
    with st.spinner("Fetching market data..."):
        data = fetch_market_data()
    if not data:
        st.error("Could not fetch market data")
        return
    snap = compute_snapshot(data)
    render_snapshot(snap)
    session["market_bias"] = snap.get("suggested_bias", "Neutral")
    save_session(session)

def page_after_close(session):
    st.header("After-Close Summary")
    st.write("Review relative strength and session notes")
    notes = st.text_area("Session notes", session.get("notes", ""))
    if st.button("Save Notes"):
        session["notes"] = notes
        save_session(session)
        st.success("Notes saved")

def page_tjr(session):
    st.header("TJR Checklist")
    st.write("Liquidity sweep + MSS + FVG/OB")
    sweep = st.checkbox("Liquidity sweep occurred")
    mss = st.checkbox("Market structure shift (MSS)")
    zone = st.checkbox("Price in FVG or Order Block")
    if sweep and mss and zone:
        st.success("Valid TJR setup")
    else:
        st.info("Waiting for full confluence")

def page_equity(session):
    st.header("Equity Checklist")
    st.write("VCP + Pivot Break + RVOL")
    vcp = st.checkbox("Volatility Contraction Pattern")
    pivot = st.checkbox("Pivot break")
    rvol = st.checkbox("Elevated RVOL")
    if vcp and pivot and rvol:
        st.success("Valid equity setup")
    else:
        st.info("Waiting for full confluence")

def page_risk():
    st.header("Risk Calculator")
    account = st.number_input("Account size", value=10000.0)
    risk_pct = st.number_input("Risk %", value=1.0)
    entry = st.number_input("Entry price", value=100.0)
    stop = st.number_input("Stop price", value=98.0)
    if entry != stop:
        risk_per_share = abs(entry - stop)
        shares = int((account * (risk_pct / 100)) / risk_per_share)
        st.metric("Shares to buy", shares)
        st.metric("Dollar risk", round(shares * risk_per_share, 2))

def page_plans(session):
    st.header("Decision Tree & Trade Plans")
    st.subheader("Quick Decision Tree")
    st.write("1. Pre-market scan - set bias")
    st.write("2. Map Asia / London / PDH / PDL")
    st.write("3. Sweep + MSS + zone? - TJR plan")
    st.write("4. High-RVOL + VCP pivot break? - Equity plan")
    st.write("5. Only take A / A+ setups")
    bias = st.selectbox("Override bias for today", ["Bullish", "Neutral", "Bearish"])
    session["market_bias"] = bias
    save_session(session)
    st.subheader("Active Trade Plans")
    plans = session.get("trade_plans", [])
    if not plans:
        st.info("No trade plans yet")
    else:
        for i, p in enumerate(plans):
            with st.expander(f"{i+1}. {p.get('type', 'Plan')}"):
                st.json(p)

def page_session(session):
    st.header("Today's Session")
    st.write(f"**Date:** {session.get('date')}")
    st.write(f"**Bias:** {session.get('market_bias', 'Neutral')}")
    st.write(f"**Plans:** {len(session.get('trade_plans', []))}")
    st.download_button(
        "Download session JSON",
        data=json.dumps(session, indent=2),
        file_name=f"edgedesk_{today_str()}.json",
        mime="application/json"
    )

def main():
    st.title("EdgeDesk")
    st.caption("Clean trading desk - TJR + Minervini - Live data")
    session = load_session()
    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio(
            "Go to",
            [
                "Pre-Market Scan",
                "After-Close Summary",
                "TJR Checklist",
                "Equity Checklist",
                "Risk Calculator",
                "Trade Plans & Tree",
                "Today's Session"
            ],
            label_visibility="collapsed"
        )
        st.divider()
        st.write(f"**Date:** {session.get('date')}")
        st.write(f"**Bias:** {session.get('market_bias', 'Neutral')}")
        st.write(f"**Plans:** {len(session.get('trade_plans', []))}")
        if st.button("Clear cache & refresh"):
            st.cache_data.clear()
            st.rerun()
    if page == "Pre-Market Scan":
        page_pre_market(session)
    elif page == "After-Close Summary":
        page_after_close(session)
    elif page == "TJR Checklist":
        page_tjr(session)
    elif page == "Equity Checklist":
        page_equity(session)
    elif page == "Risk Calculator":
        page_risk()
    elif page == "Trade Plans & Tree":
        page_plans(session)
    elif page == "Today's Session":
        page_session(session)

if __name__ == "__main__":
    main()
