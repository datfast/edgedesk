import streamlit as st
import yfinance as yf
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json
from pathlib import Path

DATA_DIR = Path("edgedesk_data")
DATA_DIR.mkdir(exist_ok=True)

INDICES = ["SPY", "QQQ", "IWM"]
KEY_STOCKS = ["NVDA", "TSLA", "AMD", "AAPL", "META", "AMZN", "MSFT", "GOOGL"]

st.set_page_config(page_title="EdgeDesk", page_icon="📊", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
    color: #1e293b;
}
.main .block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 860px;
}
h1, h2, h3 {
    color: #0f172a;
    font-weight: 650;
}
[data-testid="stMetric"] {
    background: #ffffff;
    border-radius: 12px;
    padding: 12px 16px;
    border: 1px solid #cbd5e1;
}
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    background: #0f172a;
    color: white;
    border: none;
}
.stExpander {
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #cbd5e1;
}
</style>
""", unsafe_allow_html=True)

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def load_session():
    try:
        path = DATA_DIR / f"session_{today_str()}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return {"date": today_str(), "watchlist": [], "notes": "", "profile": {}}

def save_session(session):
    try:
        path = DATA_DIR / f"session_{today_str()}.json"
        with open(path, "w") as f:
            json.dump(session, f, indent=2)
    except Exception:
        pass

def get_price(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None

def show_chart(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="6mo")
        if hist.empty:
            st.caption("Chart unavailable")
            return
        hist["MA20"] = hist["Close"].rolling(20).mean()
        hist["MA50"] = hist["Close"].rolling(50).mean()
        delta = hist["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        hist["RSI"] = 100 - (100 / (1 + rs))

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.7, 0.3]
        )
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"], name="Price"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist["MA20"], name="MA20", line=dict(color="#f59e0b", width=1.2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist["MA50"], name="MA50", line=dict(color="#3b82f6", width=1.2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist["RSI"], name="RSI", line=dict(color="#8b5cf6")), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", row=2, col=1)
        fig.update_layout(
            height=380,
            margin=dict(l=8, r=8, t=24, b=8),
            xaxis_rangeslider_visible=False,
            showlegend=True,
            title=ticker
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.caption("Chart unavailable")

def get_stocktwits_trending():
    try:
        r = requests.get("https://api.stocktwits.com/api/2/trending/symbols.json", timeout=6)
        if r.status_code != 200:
            return []
        symbols = r.json().get("symbols", [])[:5]
        out = []
        for s in symbols:
            ticker = s.get("symbol", "")
            if not ticker:
                continue
            sent = "Neutral"
            if isinstance(s.get("sentiment"), dict):
                sent = s["sentiment"].get("basic", "Neutral")
            out.append({"ticker": ticker, "sentiment": sent})
        return out
    except Exception:
        return []

def get_news(ticker):
    try:
        news = yf.Ticker(ticker).news or []
        items = []
        for n in news[:6]:
            title = n.get("title") or n.get("headline") or ""
            if title:
                items.append(title)
        return items
    except Exception:
        return []

def morning_summary():
    st.subheader("Morning Snapshot")
    cols = st.columns(3)
    for i, t in enumerate(INDICES):
        p = get_price(t)
        cols[i].metric(t, f"${p}" if p else "—")

    st.write("**Names to check**")
    for t in KEY_STOCKS[:5]:
        p = get_price(t)
        if p:
            st.write(f"• **{t}**  ${p}")

def page_main(session):
    st.header("EdgeDesk")
    morning_summary()

    st.subheader("Stocktwits")
    trending = get_stocktwits_trending()
    if trending:
        for item in trending:
            st.write(f"**{item['ticker']}** — {item['sentiment']}")
    else:
        st.caption("Trending data unavailable")

    st.subheader("Look up")
    ticker = st.text_input("Ticker", placeholder="e.g. NVDA").upper()
    if ticker:
        price = get_price(ticker)
        if price:
            st.metric(ticker, f"${price}")
            show_chart(ticker)
            news = get_news(ticker)
            if news:
                with st.expander("Recent headlines"):
                    for title in news:
                        st.write(f"• {title}")
        else:
            st.warning("No data")

    st.subheader("Watchlist")
    new_t = st.text_input("Add ticker").upper()
    if st.button("Add") and new_t:
        session.setdefault("watchlist", []).append(new_t)
        save_session(session)
        st.rerun()
    for i, t in enumerate(session.get("watchlist", [])):
        c1, c2 = st.columns([4, 1])
        c1.write(t)
        if c2.button("×", key=f"rm{i}"):
            session["watchlist"].pop(i)
            save_session(session)
            st.rerun()

    st.subheader("Risk")
    rt = st.text_input("Ticker", "NVDA", key="risk_t").upper()
    risk_amt = st.number_input("Dollar risk", value=100.0)
    stop_pct = st.number_input("Stop %", value=2.0)
    if st.button("Calculate"):
        price = get_price(rt)
        if price:
            stop = round(price * (1 - stop_pct / 100), 2)
            diff = price - stop
            shares = int(risk_amt / diff) if diff > 0 else 0
            st.write(f"Price ${price} · Stop ${stop} · Shares {shares}")
        else:
            st.warning("No price")

def page_news():
    st.header("News")
    ticker = st.text_input("Ticker", "NVDA").upper()
    if st.button("Load") or ticker:
        items = get_news(ticker)
        if items:
            for title in items:
                st.write(f"• {title}")
        else:
            st.info("No headlines found")

def page_notes(session):
    st.header("Notes")
    notes = st.text_area("Today", session.get("notes", ""), height=160)
    if st.button("Save"):
        session["notes"] = notes
        save_session(session)
        st.success("Saved")

def page_learn():
    st.header("Styles")
    st.write("**Day** — In and out same day. Tight risk.")
    st.write("**Swing** — Hold several days to a few weeks.")
    st.write("**Sweep** — Wait for a liquidity grab, then a structure shift.")
    st.write("**Position** — Hold weeks to months with wider risk.")

def main():
    session = load_session()
    page = st.sidebar.radio("Go", ["Home", "News", "Notes", "Learn"])
    if page == "Home":
        page_main(session)
    elif page == "News":
        page_news()
    elif page == "Notes":
        page_notes(session)
    else:
        page_learn()

if __name__ == "__main__":
    main()
