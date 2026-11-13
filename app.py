#!/usr/bin/env python3
"""
EdgeDesk App – Simple Streamlit web interface
All the TJR + Minervini + market-scan logic in a clean, updatable app.
"""

from __future__ import annotations
import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIG & DATA
# ─────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "edgedesk_data"
DATA_DIR.mkdir(exist_ok=True)

INDICES = ["SPY", "QQQ", "IWM"]
VIX = "^VIX"
KEY_STOCKS = ["NVDA", "TSLA", "AMD", "AAPL", "META", "AMZN", "PLTR", "MSFT", "GOOGL", "AVGO"]
ALL_TICKERS = INDICES + [VIX] + KEY_STOCKS

st.set_page_config(
    page_title="EdgeDesk",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)# ── Bright, clean, eye-appealing theme ──────────────────────────────
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
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #334155;
    }
    h1 {
        color: #0f172a !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }
    h2, h3 {
        color: #1e293b !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="stMetricLabel"] {
        color: #64748b !important;
        font-size: 0.85rem !important;
    }
    [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        transition: all 0.15s ease;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
        transform: translateY(-1px);
    }
    .stButton > button[kind="secondary"] {
        background: #f1f5f9;
        color: #334155;
        border: 1px solid #e2e8f0;
    }
    [data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        background: #ffffff;
    }
    .stSuccess {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-radius: 10px;
        color: #065f46;
    }
    .stInfo {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 10px;
        color: #1e40af;
    }
    .stWarning {
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-radius: 10px;
        color: #92400e;
    }
    .stError {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 10px;
        color: #991b1b;
    }
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    .stRadio label, .stCheckbox label {
        color: #334155 !important;
    }
    [data-testid="stSidebar"] .stRadio > div {
        gap: 0.35rem;
    }
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #64748b !
        # ─────────────────────────────────────────────
# SESSION HELPERS
# ─────────────────────────────────────────────
def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load_session() -> dict:
    path = DATA_DIR / f"session_{today_str()}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        "date": today_str(),
        "market_bias": "Neutral",
        "pre_market": {},
        "after_close": {},
        "levels": {},
        "tjr_setups": [],
        "equity_setups": [],
        "trade_plans": [],
        "notes": "",
    }


def save_session(data: dict):
    path = DATA_DIR / f"session_{today_str()}.json"
    clean = json.loads(json.dumps(data, default=str))
    with open(path, "w") as f:
        json.dump(clean, f, indent=2)


# ─────────────────────────────────────────────
# MARKET DATA
# ─────────────────────────────────────────────
@st.cache_data(ttl=60 * 5)
def fetch_market_data(period: str = "5d") -> Dict[str, pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError:
        return {}

    results = {}
    for t in ALL_TICKERS:
        try:
            hist = yf.Ticker(t).history(period=period, auto_adjust=True)
            if not hist.empty:
                results[t] = hist
        except Exception:
            continue
    return results
    def compute_snapshot(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
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
        gap_pct = ((last["Open"] - prev["Close"]) / prev["Close"]) * 100 if "Open" in last else 0.0

        snap["indices"][t] = {
            "last": round(float(last["Close"]), 2),
            "change_pct": round(float(change_pct), 2),
            "gap_pct": round(float(gap_pct), 2),
            "volume": int(last.get("Volume", 0)),
            "high": round(float(last["High"]), 2),
            "low": round(float(last["Low"]), 2),
        }

    if VIX in data and not data[VIX].empty:
        v = float(data[VIX].iloc[-1]["Close"])
        snap["vix"] = round(v, 2)
        if v > 25:
            snap["notes"].append("Elevated VIX – higher volatility expected")
        elif v < 15:
            snap["notes"].append("Low VIX – complacency risk")

    for t in KEY_STOCKS:
        if t not in data or data[t].empty:
            continue
        df = data[t]
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        change_pct = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100
        vol = last.get("Volume", 0)
        avg_vol = df["Volume"].tail(5).mean() if "Volume" in df else 1
        rvol = float(vol / avg_vol) if avg_vol > 0 else 1.0

        snap["stocks"][t] = {
            "last": round(float(last["Close"]), 2),
            "change_pct": round(float(change_pct), 2),
            "rvol": round(rvol, 2),
            "volume": int(vol),
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
    def render_snapshot(snap: Dict[str, Any]):
    st.caption(f"As of {snap.get('timestamp', '—')}")

    cols = st.columns(4)
    for i, t in enumerate(INDICES):
        info = snap.get("indices", {}).get(t)
        if info:
            delta = f"{info['change_pct']:+.2f}%"
            cols[i].metric(t, f"{info['last']:.2f}", delta)

    if snap.get("vix") is not None:
        cols[3].metric("VIX", f"{snap['vix']:.2f}")

    st.markdown(f"**Suggested Bias:** `{snap.get('suggested_bias', 'Neutral')}`")
    for note in snap.get("notes", []):
        st.info(note)

    stocks = snap.get("stocks", {})
    if stocks:
        rows = []
        for t, info in sorted(stocks.items(), key=lambda x: x[1]["change_pct"], reverse=True):
            rows.append({
                "Ticker": t,
                "Last": info["last"],
                "Chg %": info["change_pct"],
                "RVOL": info["rvol"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        high_rvol = [t for t, info in stocks.items() if info.get("rvol", 0) >= 1.8]
        if high_rvol:
            st.success(f"Elevated RVOL names: {', '.join(high_rvol)}")

def page_pre_market(session: dict):
    st.header("Pre-Market / Live Market Scan")
    st.write("Live data for indices, VIX and key stocks. Use this to set bias before the open.")

    if st.button("🔄 Refresh Market Data", type="primary"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Fetching market data..."):
        data = fetch_market_data()
        if not data:
            st.error("Could not fetch market data. Check connection.")
            return
        snap = compute_snapshot(data)

    render_snapshot(snap)

    session["pre_market"] = snap
    session["market_bias"] = snap.get("suggested_bias", session.get("market_bias", "Neutral"))
    save_session(session)
    st.success("Snapshot saved to today's session.")
    def page_after_close(session: dict):
    st.header("After-Close Summary")
    st.write("End-of-day relative strength and preparation notes for tomorrow.")

    if st.button("🔄 Refresh After-Close Data", type="primary"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Fetching market data..."):
        data = fetch_market_data()
        if not data:
            st.error("Could not fetch market data.")
            return
        snap = compute_snapshot(data)

    render_snapshot(snap)

    spy_chg = snap.get("indices", {}).get("SPY", {}).get("change_pct", 0)
    leaders, laggards = [], []
    for t, info in snap.get("stocks", {}).items():
        rel = info["change_pct"] - spy_chg
        if rel > 1.0:
            leaders.append((t, info["change_pct"], rel))
        elif rel < -1.0:
            laggards.append((t, info["change_pct"], rel))

    leaders.sort(key=lambda x: x[2], reverse=True)
    laggards.sort(key=lambda x: x[2])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("RS Leaders vs SPY")
        if leaders:
            for t, chg, rel in leaders[:6]:
                st.write(f"**{t}**: {chg:+.2f}% (RS {rel:+.2f}%)")
        else:
            st.write("None significant")

    with col2:
        st.subheader("Relative Weakness")
        if laggards:
            for t, chg, rel in laggards[:6]:
                st.write(f"**{t}**: {chg:+.2f}% (RS {rel:+.2f}%)")
        else:
            st.write("None significant")

    st.subheader("Tomorrow Notes")
    bias = snap.get("suggested_bias", "Neutral")
    if bias == "Bullish":
        st.success("Bias leans bullish → favor long-side VCP / continuation and long liquidity sweeps")
    elif bias == "Bearish":
        st.warning("Bias leans bearish → prioritize short-side sweeps and weak RS names")
    else:
        st.info("Neutral / mixed → wait for clear NY open structure")

    if leaders:
        st.write(f"Watch RS leaders: {', '.join([x[0] for x in leaders[:3]])}")

    session["after_close"] = snap
    session["market_bias"] = bias
    save_session(session)
    st.success("After-close data saved.")
    def page_tjr(session: dict):
    st.header("TJR Futures Checklist (ES / NQ)")
    st.markdown("**Core sequence:** Liquidity Sweep → Market Structure Shift → Retrace into FVG / Order Block")

    st.info(f"Current data bias: **{session.get('market_bias', 'Neutral')}**")

    with st.expander("1. Key Levels", expanded=True):
        levels = session.get("levels", {})
        cols = st.columns(3)
        for i, name in enumerate(["Asia High", "Asia Low", "London High", "London Low", "PDH", "PDL"]):
            levels[name] = cols[i % 3].text_input(name, value=str(levels.get(name, "")))
        session["levels"] = levels

    swept = st.checkbox("Price swept a clear liquidity pool (Asia / London / PDH / PDL)?")
    if not swept:
        st.warning("No sweep → no TJR setup.")
        save_session(session)
        return

    pool = st.text_input("Which pool was swept?")
    direction = st.radio("Expected direction after sweep", ["long", "short"], horizontal=True)

    mss = st.checkbox("Strong displacement candle closed beyond recent swing (MSS / BOS)?")
    if not mss:
        st.warning("No structure shift yet.")
        save_session(session)
        return

    zone = st.selectbox("Entry zone type", ["FVG", "Order Block", "50% Equilibrium", "Other"])
    zone_level = st.text_input("Approximate price of the zone")

    st.subheader("Confluences")
    confs = []
    if st.checkbox("Inverse Fair Value Gap"):
        confs.append("Inverse FVG")
    if st.checkbox("SMT divergence (ES vs NQ)"):
        confs.append("SMT")
    if st.checkbox("Strong displacement body"):
        confs.append("Strong displacement")
    if st.checkbox("Within NY killzone (9:30–11:00 ET)"):
        confs.append("NY Killzone")
    if session.get("market_bias", "").lower() == direction:
        confs.append("Aligns with data bias")
        st.success("+ Aligns with market data bias")

    score = 3 + len(confs)
    if score >= 6:
        quality = "A+"
    elif score >= 4:
        quality = "A"
    else:
        quality = "B"

    st.metric("Setup Quality", f"{quality} ({score}/8)")

    instrument = st.text_input("Instrument", value="NQ")
    if st.button("Add to Trade Plans", type="primary"):
        plan = {
            "type": "TJR Futures",
            "instrument": instrument,
            "direction": direction,
            "swept_pool": pool,
            "zone": zone,
            "zone_level": zone_level,
            "confluences": confs,
            "score": score,
            "quality": quality,
            "timestamp": datetime.now().isoformat(timespec="minutes"),
        }
        session.setdefault("tjr_setups", []).append(plan)
        session.setdefault("trade_plans", []).append(plan)
        save_session(session)
        st.success(f"Added {quality} TJR plan for {instrument}")
        st.rerun()
        def page_equity(session: dict):
    st.header("Minervini-Style Equity Checklist")

    pre = session.get("pre_market", {})
    high_rvol = [t for t, info in pre.get("stocks", {}).items() if info.get("rvol", 0) >= 1.5]
    if high_rvol:
        st.info(f"High RVOL from scan: {', '.join(high_rvol)}")

    ticker = st.text_input("Ticker", value="").upper()
    if not ticker:
        return

    st.subheader("Pre-conditions")
    stage2 = st.checkbox("Stage 2 uptrend (Trend Template roughly ok)")
    rs = st.checkbox("Strong relative strength")
    liquid = st.checkbox("Liquid (good average volume)")

    if not (stage2 and rs and liquid):
        st.warning("Does not meet basic pre-conditions.")
        return

    st.subheader("VCP Structure")
    contractions = st.number_input("Number of contractions (2–6 ideal)", min_value=1, max_value=8, value=3)
    tightening = st.checkbox("Contractions progressively tighter")
    volume_dry = st.checkbox("Volume drying up on final contraction")

    if not (tightening and volume_dry):
        st.warning("VCP not clean enough.")
        return

    st.subheader("Entry Trigger")
    pivot = st.number_input("Pivot price (high of final contraction)", min_value=0.0, value=0.0, format="%.2f")
    broken = st.checkbox("Price broke & closed above pivot on expanding volume")

    if not broken:
        st.info("Waiting for pivot break. You can still add as a watch idea.")
        if st.button("Add as Watch Idea"):
            session.setdefault("equity_setups", []).append({
                "ticker": ticker,
                "status": "Watching for pivot break",
                "pivot": pivot,
                "timestamp": datetime.now().isoformat(timespec="minutes"),
            })
            save_session(session)
            st.success("Watch idea added")
        return

    stop = st.number_input("Stop price (below final contraction low)", min_value=0.0, value=0.0, format="%.2f")
    quality = "A+" if contractions >= 3 and volume_dry else "A"

    if st.button("Add to Trade Plans", type="primary"):
        plan = {
            "type": "Minervini Equity",
            "ticker": ticker,
            "direction": "long",
            "pivot": pivot,
            "stop": stop,
            "quality": quality,
            "contractions": contractions,
            "timestamp": datetime.now().isoformat(timespec="minutes"),
        }
        session.setdefault("equity_setups", []).append(plan)
        session.setdefault("trade_plans", []).append(plan)
        save_session(session)
        st.success(f"{ticker} added as {quality} equity setup")
        st.rerun()
        def page_risk():
    st.header("Risk Calculator")
    account = st.number_input("Account size ($)", min_value=100.0, value=10000.0, step=100.0)
    risk_pct = st.number_input("Risk per trade (%)", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
    risk_dollars = account * (risk_pct / 100)
    st.metric("Max risk this trade", f"${risk_dollars:,.2f}")

    col1, col2, col3 = st.columns(3)
    entry = col1.number_input("Entry price", min_value=0.0, value=0.0, format="%.2f")
    stop = col2.number_input("Stop price", min_value=0.0, value=0.0, format="%.2f")
    direction = col3.radio("Direction", ["long", "short"], horizontal=True)

    if entry > 0 and stop > 0:
        risk_per_unit = (entry - stop) if direction == "long" else (stop - entry)
        if risk_per_unit <= 0:
            st.error("Invalid stop – risk per unit must be positive.")
            return
        size = risk_dollars / risk_per_unit
        st.success(f"Position size: **{size:.2f}** units/shares/contracts")
        st.write(f"Risk per unit: ${risk_per_unit:.2f}")

        st.subheader("Target prices")
        tcols = st.columns(4)
        for i, r in enumerate([1.5, 2.0, 3.0, 4.0]):
            tp = entry + (risk_per_unit * r) if direction == "long" else entry - (risk_per_unit * r)
            tcols[i].metric(f"{r}R", f"{tp:.2f}")
            def page_plans(session: dict):
    st.header("Decision Tree & Trade Plans")

        st.subheader("Quick Decision Tree")
    st.write("1. Pre-market scan - set bias")
    st.write("2. Map Asia / London / PDH / PDL")
    st.write("3. Sweep + MSS + zone? - TJR plan")
    st.write("4. High-RVOL + VCP pivot break? - Equity plan")
    st.write("5. Only take A / A+ setups")
    bias = st.selectbox(
        "Override bias for today",
        ["Bullish", "Neutral", "Bearish"],
        index=["Bullish", "Neutral", "Bearish"].index(session.get("market_bias", "Neutral")),
    )
    session["market_bias"] = bias

    st.subheader("Active Trade Plans")
    plans = session.get("trade_plans", [])
    if not plans:
        st.info("No trade plans yet. Complete a checklist first.")
    else:
        for i, p in enumerate(plans):
            with st.expander(f"{i+1}. {p.get('type')} – {p.get('instrument') or p.get('ticker')} ({p.get('quality')})"):
                st.json(p)
                if st.button(f"Remove plan {i+1}", key=f"rm_{i}"):
                    plans.pop(i)
                    session["trade_plans"] = plans
                    save_session(session)
                    st.rerun()

    notes = st.text_area("Daily notes", value=session.get("notes", ""))
    session["notes"] = notes
    if st.button("Save Session"):
        save_session(session)
        st.success("Saved")
      def page_session(session: dict):
    st.header(f"Today's Session – {session.get('date')}")
    st.write(f"**Bias:** {session.get('market_bias', '—')}")

    if session.get("pre_market"):
        with st.expander("Pre-market snapshot"):
            render_snapshot(session["pre_market"])

    if session.get("after_close"):
        with st.expander("After-close snapshot"):
            render_snapshot(session["after_close"])

    if session.get("levels"):
        st.write("**Levels:**", session["levels"])

    st.write("**Trade Plans:**", len(session.get("trade_plans", [])))
    st.write("**Notes:**", session.get("notes") or "—")

    st.download_button(
        "Download session JSON",
        data=json.dumps(session, indent=2, default=str),
        file_name=f"edgedesk_{today_str()}.json",
        mime="application/json",
    )


def main():
            st.title("EdgeDesk")
    st.caption("Clean trading desk - TJR - Minervini - Live data")

    st.caption("On phone: open in Safari/Chrome → Share → Add to Home Screen for app-like use.")

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
                "Trade Plans &
                      "Today's Session",
            ],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown(f"**Date**  \n{session['date']}")
        st.markdown(f"**Bias**  \n`{session.get('market_bias', '—')}`")
        st.markdown(f"**Plans**  \n{len(session.get('trade_plans', []))}")
        st.divider()
        if st.button("🔄 Clear cache & refresh", use_container_width=True):
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
