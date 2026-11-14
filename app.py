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
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 880px;
}
h1, h2, h3 {
    color: #0f172a;
    font-weight: 650;
}
[data-testid="stMetric"] {
    background: #ffffff;
    border-radius: 14px;
    padding: 14px 18px;
    border: 1px solid #cbd5e1;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}
.stButton > button {
    border-radius: 10px;
    font-weight: 500;
    background: #0f172a;
    color: white;
    border: none;
}
.stExpander {
    background: #ffffff;
    border-radius: 14px;
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
            x=hist.index,
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            name="Price"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["MA20"],
            name="MA20", line=dict(color="#f59e0b", width=1.2)
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["MA50"],
            name="MA50", line=dict(color="#3b82f6", width=1.2)
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["RSI"],
            name="RSI", line=dict(color="#8b5cf6")
        ), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", row=2, col=1)
        fig.update_layout(
            height=420,
            margin=dict(l=8, r=8, t=28, b=8),
            xaxis_rangeslider_visible=False,
            showlegend=True,
            title=ticker
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.caption("Chart unavailable")

def get_stocktwits_trending():
    try:
        r = requests.get(
            "https://api.stocktwits.com/api/2/trending/symbols.json",
            timeout=5
        )
        if r.status_code != 200:
            return []
        data = r.json()
        symbols = data.get("symbols", [])[:6]
        out = []
        for s in symbols:
            sent = "Neutral"
            if isinstance(s.get("sentiment"), dict):
                sent = s["sentiment"].get("basic", "Neutral")
            ticker = s.get("symbol", "")
            if ticker:
                out.append({"ticker": ticker, "sentiment": sent})
        return out
    except Exception:
        return []

def get_stocktwits_sentiment(ticker):
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        messages = data.get("messages", [])
        bull = 0
        bear = 0
        for m in messages:
            basic = m.get("entities", {}).get("sentiment", {}).get("basic")
            if basic == "Bullish":
                bull += 1
            elif basic == "Bearish":
                bear += 1
        if bull + bear == 0:
            return "Neutral"
        if bull > bear:
            return "Bullish"
        if bear > bull:
            return "Bearish"
        return "Neutral"
    except Exception:
        return None

def get_simple_recs():
    recs = []
    for t in KEY_STOCKS[:6]:
        price = get_price(t)
        if price:
            recs.append({"ticker": t, "price": price})
    return recs

def page_main(session):
    st.header("EdgeDesk")

    with st.expander("Profile"):
        name = st.text_input("Name", value=session.get("profile", {}).get("name", ""))
        if st.button("Save Profile"):
            session["profile"] = {"name": name}
            save_session(session)
            st.success("Saved")

    st.subheader("Market")
    cols = st.columns(3)
    for i, t in enumerate(INDICES):
        cols[i].metric(t, get_price(t) or "-")

    st.subheader("Stocktwits Trending")
    trending = get_stocktwits_trending()
    if trending:
        for item in trending:
            st.write(f"**{item['ticker']}** — {item['sentiment']}")
    else:
        st.caption("Trending unavailable right now")

    st.subheader("Quick Watch")
    recs = get_simple_recs()
    if recs:
        for r in recs:
            st.write(f"**{r['ticker']}**  ${r['price']}")

    st.subheader("Look up stock")
    ticker = st.text_input("Ticker").upper()
    if ticker:
        price = get_price(ticker)
        if price:
            st.metric(ticker, f"${price}")
            sent = get_stocktwits_sentiment(ticker)
            if sent:
                st.caption(f"Stocktwits: {sent}")
            show_chart(ticker)
        else:
            st.warning("No price data")

    st.subheader("Watchlist")
    new_ticker = st.text_input("Add to watchlist").upper()
    if st.button("Add") and new_ticker:
        session.setdefault("watchlist", []).append(new_ticker)
        save_session(session)
        st.rerun()
    for i, t in enumerate(session.get("watchlist", [])):
        c1, c2 = st.columns([3, 1])
        c1.write(t)
        if c2.button("Remove", key=f"rm{i}"):
            session["watchlist"].pop(i)
            save_session(session)
            st.rerun()

    st.subheader("Risk Calculator")
    risk_ticker = st.text_input("Risk ticker", "NVDA").upper()
    risk_amount = st.number_input("Dollar risk", value=100.0)
    stop_pct = st.number_input("Stop %", value=2.0)
    if st.button("Calculate"):
        price = get_price(risk_ticker)
        if price:
            stop = round(price * (1 - stop_pct / 100), 2)
            diff = price - stop
            shares = int(risk_amount / diff) if diff > 0 else 0
            st.write(f"Price: ${price}")
            st.write(f"Stop: ${stop}")
            st.write(f"Shares: {shares}")
        else:
            st.warning("No price")

    st.subheader("Trade")
    st.markdown("[Robinhood](https://robinhood.com) • [Coinbase](https://www.coinbase.com) • [E*TRADE](https://us.etrade.com)")

def page_news():
    st.header("News")
    ticker = st.text_input("Ticker", "NVDA").upper()
    if st.button("Get News"):
        try:
            news = yf.Ticker(ticker).news or []
            if news:
                for item in news[:5]:
                    st.write(item.get("title", ""))
            else:
                st.info("No news")
        except Exception:
            st.info("Could not load news")

def page_notes(session):
    st.header("Notes")
    notes = st.text_area("Notes", session.get("notes", ""))
    if st.button("Save Notes"):
        session["notes"] = notes
        save_session(session)
        st.success("Saved")

def page_learn():
    st.header("Learn")
    st.write("**Day Trading** — Same day, tight stops.")
    st.write("**Swing Trading** — Hold days to weeks.")
    st.write("**Liquidity Sweep** — Sweep then structure shift.")
    st.write("**Position Trading** — Hold weeks to months.")

def main():
    session = load_session()
    page = st.sidebar.radio("Pages", ["Main", "News", "Notes", "Learn"])
    if page == "Main":
        page_main(session)
    elif page == "News":
        page_news()
    elif page == "Notes":
        page_notes(session)
    else:
        page_learn()

if __name__ == "__main__":
    main()
