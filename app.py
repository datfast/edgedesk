import streamlit as st
import yfinance as yf
import requests
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
.stApp { background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%); color: #1e293b; }
.main .block-container { padding-top: 1.5rem; max-width: 1000px; }
h1, h2, h3 { color: #0f172a; font-weight: 600; }
[data-testid="stMetric"] {
    background: #ffffff; border-radius: 12px; padding: 12px 16px;
    border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stButton > button { border-radius: 8px; font-weight: 500; }
.stExpander { background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def load_session():
    path = DATA_DIR / f"session_{today_str()}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"date": today_str(), "watchlist": [], "notes": "", "profile": {}}

def save_session(session):
    path = DATA_DIR / f"session_{today_str()}.json"
    with open(path, "w") as f:
        json.dump(session, f, indent=2)

def get_price(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None

def show_mini_chart(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1mo")
        if not hist.empty:
            st.line_chart(hist["Close"], height=160)
    except Exception:
        st.caption("Chart unavailable")

def show_company_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        name = info.get("longName", ticker)
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        summary = info.get("longBusinessSummary", "No description available.")
        st.markdown(f"**{name}**")
        st.write(f"**Sector:** {sector}  •  **Industry:** {industry}")
        st.write(summary[:400] + "..." if len(summary) > 400 else summary)
    except Exception:
        st.caption("Company info unavailable")

def get_stocktwits_trending():
    try:
        data = requests.get("https://api.stocktwits.com/api/2/trending/symbols.json", timeout=5).json()
        symbols = data.get("symbols", [])[:8]
        results = []
        for s in symbols:
            sent = "Neutral"
            if s.get("sentiment"):
                sent = s["sentiment"].get("basic", "Neutral")
            results.append({"ticker": s.get("symbol"), "title": s.get("title", ""), "sentiment": sent})
        return results
    except Exception:
        return []

def get_stocktwits_sentiment(ticker):
    try:
        data = requests.get(f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json", timeout=5).json()
        messages = data.get("messages", [])
        bull = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish")
        bear = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish")
        if bull + bear == 0:
            return "Neutral"
        return "Bullish" if bull > bear else "Bearish" if bear > bull else "Neutral"
    except Exception:
        return None

def get_recommendations():
    recs = []
    for t in KEY_STOCKS:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if hist.empty:
                continue
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last
            chg = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100
            vol = last.get("Volume", 0)
            avg = hist["Volume"].tail(5).mean() if "Volume" in hist else 1
            rvol = vol / avg if avg > 0 else 1
            if chg > 0.3 and rvol >= 1.2:
                recs.append({
                    "ticker": t,
                    "price": round(float(last["Close"]), 2),
                    "change": round(chg, 2),
                    "rvol": round(rvol, 2)
                })
        except Exception:
            continue
    recs.sort(key=lambda x: x["rvol"], reverse=True)
    return recs

def page_main(session):
    st.header("EdgeDesk")
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()
