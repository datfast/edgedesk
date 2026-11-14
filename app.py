import streamlit as st
import yfinance as yf
from datetime import datetime
import json
from pathlib import Path

DATA_DIR = Path("edgedesk_data")
DATA_DIR.mkdir(exist_ok=True)

INDICES = ["SPY", "QQQ", "IWM"]
KEY_STOCKS = ["NVDA", "TSLA", "AMD", "AAPL", "META", "AMZN", "MSFT", "GOOGL", "AVGO", "PLTR"]

st.set_page_config(page_title="EdgeDesk", page_icon="📊", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); color: #1e293b; }
.main .block-container { padding-top: 1.2rem; max-width: 1100px; }
</style>
""", unsafe_allow_html=True)

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def load_session():
    path = DATA_DIR / f"session_{today_str()}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"date": today_str(), "watchlist": [], "notes": ""}

def save_session(session):
    path = DATA_DIR / f"session_{today_str()}.json"
    with open(path, "w") as f:
        json.dump(session, f, indent=2)

def get_price(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except:
        return None

def show_mini_chart(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1mo")
        if not hist.empty:
            st.line_chart(hist["Close"], height=180)
    except:
        st.caption("Chart unavailable")

def show_company_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        name = info.get("longName", ticker)
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        summary = info.get("longBusinessSummary", "No description available.")
        st.markdown(f"**{name}**")
        st.write(f"**Sector:** {sector}")
        st.write(f"**Industry:** {industry}")
        st.write(summary[:500] + "..." if len(summary) > 500 else summary)
    except:
        st.caption("Company info unavailable")

def page_scan():
    st.header("Pre-Market Scan")
    if st.button("Refresh"):
        st.cache_data.clear()
        st.rerun()
    cols = st.columns(4)
    for i, t in enumerate(INDICES):
        cols[i].metric(t, get_price(t) or "-")
    st.subheader("Look up any stock")
    search = st.text_input("Ticker", placeholder="e.g. NVDA").upper()
    if search:
        price = get_price(search)
        if price:
            st.metric(search, f"${price}")
            show_mini_chart(search)
            with st.expander("What is this company?"):
                show_company_info(search)
        else:
            st.warning("Ticker not found")
    st.subheader("Key Stocks")
    for t in KEY_STOCKS:
        price = get_price(t)
        with st.expander(f"{t}  •  {price or '-'}"):
            show_mini_chart(t)
            show_company_info(t)

def page_news():
    st.header("News")
    ticker = st.text_input("Ticker", "NVDA").upper()
    if st.button("Get News"):
        try:
            for item in yf.Ticker(ticker).news[:6]:
                st.markdown(f"**{item.get('title','')}**")
                st.caption(item.get("publisher",""))
                st.divider()
        except:
            st.info("No news")

def page_watchlist(session):
    st.header("Watchlist")
    c1, c2, c3 = st.columns([2,1,1])
    ticker = c1.text_input("Ticker").upper()
    side = c2.radio("Side", ["Buy","Sell"], horizontal=True, label_visibility="collapsed")
    if c3.button("Add") and ticker:
        session.setdefault("watchlist", []).append({"ticker": ticker, "side": side})
        save_session(session)
        st.rerun()
    for i, w in enumerate(session.get("watchlist", [])):
        a, b = st.columns([3,1])
        a.write(f"**{w['ticker']}** — {w['side']}")
        if b.button("Remove", key=f"rm{i}"):
            session["watchlist"].pop(i)
            save_session(session)
            st.rerun()

def page_risk():
    st.header("Risk Calculator")
    ticker = st.text_input("Ticker", "NVDA").upper()
    risk = st.number_input("Dollar risk", 100.0)
    stop_pct = st.slider("Stop %", 0.5, 5.0, 2.0)
    if st.button("Calculate"):
        price = get_price(ticker)
        if price:
            stop = round(price * (1 - stop_pct/100), 2)
            rps = price - stop
            shares = int(risk / rps) if rps > 0 else 0
            st.metric("Price", f"${price}")
            st.metric("Stop", f"${stop}")
            st.metric("Shares", shares)
            st.metric("Dollar Risk", f"${round(shares * rps, 2)}")
        else:
            st.warning("No price")

def page_notes(session):
    st.header("Notes")
    notes = st.text_area("Notes", session.get("notes",""), height=220)
    if st.button("Save"):
        session["notes"] = notes
        save_session(session)
        st.success("Saved")

def page_learn():
    st.header("Learn Trading Styles")
    st.write("Simple breakdown of common approaches and the basic steps for each.")
    with st.expander("Day Trading"):
        st.write("""
        **What it is:** Open and close trades the same day. No overnight positions.
        **How to do it:**
        1. Focus on liquid names (high volume).
        2. Wait for a clear level (previous day high/low, opening range).
        3. Enter on a strong move away from that level.
        4. Use a tight stop just beyond the level.
        5. Take profits at 1.5–3R or end of day.
        """)
    with st.expander("Swing Trading"):
        st.write("""
        **What it is:** Hold for a few days to a few weeks.
        **How to do it:**
        1. Find a stock in a clear uptrend.
        2. Wait for a pullback to support.
        3. Enter when it starts turning back up.
        4. Place stop below the recent swing low.
        5. Target the next resistance or 2–3R.
        """)
    with st.expander("Liquidity Sweep"):
        st.write("""
        **What it is:** Trade the sweep of a liquidity pool followed by a structure shift.
        **How to do it:**
        1. Mark Asia high/low, London high/low, previous day high/low.
        2. Wait for price to sweep one of those levels.
        3. Look for a strong displacement candle that closes back the other way.
        4. Enter on the retrace into a fair value gap or order block.
        5. Stop beyond the sweep high/low.
        """)
    with st.expander("Volatility Contraction"):
        st.write("""
        **What it is:** A stock tightening before a breakout.
        **How to do it:**
        1. Confirm the stock is in an uptrend.
        2. Look for 2–6 contractions that get tighter.
        3. Volume should dry up on the final contraction.
        4. Enter when price breaks above the pivot on expanding volume.
        5. Stop just below the final contraction low.
        """)
    with st.expander("Position Trading"):
        st.write("""
        **What it is:** Hold for weeks to months based on bigger trends.
        **How to do it:**
        1. Find a strong fundamental or sector trend.
        2. Enter on a weekly chart breakout or pullback.
        3. Use a wider stop.
        4. Hold as long as the bigger trend stays intact.
        5. Exit when the weekly structure breaks.
        """)

def timing_suggestion(bias, rvol, hour):
    tips = []
    if hour < 10:
        tips.append("Opening range (9:30–10:00) is still forming. Wait for a clear break.")
    elif 10 <= hour < 11:
        tips.append("Good window for liquidity sweeps and opening-range breaks.")
    elif 11 <= hour < 14:
        tips.append("Midday is usually slower. Prefer only high-quality setups.")
    else:
        tips.append("Afternoon — watch for end-of-day momentum or reversal.")
    if rvol >= 1.8:
        tips.append("High RVOL — momentum entries are more reliable.")
    if bias == "Bullish":
        tips.append("Bias is bullish — favor long entries on pullbacks.")
    elif bias == "Bearish":
        tips.append("Bias is bearish — favor short entries on rallies.")
    return tips

def page_timing():
    st.header("Entry / Exit Timing")
    ticker = st.text_input("Ticker", "NVDA").upper()
    bias = st.selectbox("Current bias", ["Bullish", "Neutral", "Bearish"])
    if st.button("Get Timing"):
        price = get_price(ticker)
        if not price:
            st.warning("Could not load ticker")
            return
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            vol = hist["Volume"].iloc[-1]
            avg = hist["Volume"].tail(5).mean()
            rvol = round(vol / avg, 2) if avg > 0 else 1
        except:
            rvol = 1
        hour = datetime.now().hour
        tips = timing_suggestion(bias, rvol, hour)
        st.metric(ticker, f"${price}")
        st.caption(f"RVOL: {rvol}")
        for tip in tips:
            st.write(f"• {tip}")
        st.info("These are guidelines based on volume and time of day, not guarantees.")

def main():
    st.title("EdgeDesk")
    session = load_session()
    page = st.sidebar.radio("Pages", ["Scan", "News", "Watchlist", "Risk", "Timing", "Notes", "Learn"])
    if page == "Scan":
        page_scan()
    elif page == "News":
        page_news()
    elif page == "Watchlist":
        page_watchlist(session)
    elif page == "Risk":
        page_risk()
    elif page == "Timing":
        page_timing()
    elif page == "Notes":
        page_notes(session)
    else:
        page_learn()

if __name__ == "__main__":
    main()
