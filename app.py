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
    background: #f8fafc;
    color: #0f172a;
}
.main .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 780px;
}
h1 {
    font-size: 1.6rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}
h2 {
    font-size: 1.15rem;
    font-weight: 600;
    margin-top: 1.4rem;
    margin-bottom: 0.5rem;
    color: #0f172a;
}
[data-testid="stMetric"] {
    background: #ffffff;
    border-radius: 12px;
    padding: 12px 14px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
[data-testid="stMetricValue"] {
    font-size: 1.15rem;
    font-weight: 600;
}
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    background: #1e293b;
    color: white;
    border: none;
    padding: 0.35rem 0.9rem;
}
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    border-radius: 8px;
    border: 1px solid #cbd5e1;
}
.stPlotlyChart {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
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
    return {"date": today_str(), "watchlist": [], "notes": ""}

def save_session(session):
    try:
        path = DATA_DIR / f"session_{today_str()}.json"
        with open(path, "w") as f:
            json.dump(session, f, indent=2)
    except Exception:
        pass

def get_quote(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="2d")
        if hist.empty:
            return None
        price = round(float(hist["Close"].iloc[-1]), 2)
        change = 0.0
        if len(hist) > 1:
            prev = float(hist["Close"].iloc[-2])
            change = round((price - prev) / prev * 100, 2)
        return {"price": price, "change": change}
    except Exception:
        return None

def get_technical_bias(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="6mo")
        if hist.empty or len(hist) < 50:
            return None
        close = hist["Close"]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1]
        price = close.iloc[-1]

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        notes = []
        bias = "Neutral"

        if price > ma20 and price > ma50:
            notes.append("Price above both MAs")
            bias = "Bullish"
        elif price < ma20 and price < ma50:
            notes.append("Price below both MAs")
            bias = "Bearish"
        else:
            notes.append("Price mixed vs MAs")

        if rsi < 30:
            notes.append("RSI oversold")
            if bias == "Neutral":
                bias = "Bullish"
        elif rsi > 70:
            notes.append("RSI overbought")
            if bias == "Neutral":
                bias = "Bearish"
        else:
            notes.append(f"RSI {round(rsi, 1)}")

        return {"bias": bias, "notes": notes}
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
            vertical_spacing=0.03,
            row_heights=[0.74, 0.26]
        )
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"],
            name="Price"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["MA20"],
            name="MA20", line=dict(color="#f59e0b", width=1.3)
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["MA50"],
            name="MA50", line=dict(color="#3b82f6", width=1.3)
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["RSI"],
            name="RSI", line=dict(color="#8b5cf6", width=1.5)
        ), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", row=2, col=1)
        fig.update_layout(
            height=390,
            margin=dict(l=10, r=10, t=32, b=10),
            xaxis_rangeslider_visible=False,
            showlegend=True,
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            title=dict(text=ticker, font=dict(size=15))
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

def page_main(session):
    st.title("EdgeDesk")

    st.subheader("Market")
    cols = st.columns(3)
    for i, t in enumerate(INDICES):
        q = get_quote(t)
        if q:
            cols[i].metric(t, f"${q['price']}", f"{q['change']:+.2f}%")
        else:
            cols[i].metric(t, "—")

    st.subheader("Focus")
    fcols = st.columns(4)
    for i, t in enumerate(KEY_STOCKS[:4]):
        q = get_quote(t)
        if q:
            fcols[i].metric(t, f"${q['price']}", f"{q['change']:+.2f}%")

    st.subheader("Trending")
    trending = get_stocktwits_trending()
    if trending:
        tcols = st.columns(len(trending))
        for i, item in enumerate(trending):
            tcols[i].markdown(f"**{item['ticker']}**\n\n{item['sentiment']}")
    else:
        st.caption("Unavailable")

    st.subheader("Chart")
    ticker = st.text_input("Ticker", placeholder="NVDA, TSLA…").strip().upper()
    if ticker:
        q = get_quote(ticker)
        if q:
            st.metric(ticker, f"${q['price']}", f"{q['change']:+.2f}%")
            bias = get_technical_bias(ticker)
            if bias:
                st.write(f"**Bias:** {bias['bias']}")
                for n in bias["notes"]:
                    st.caption(n)
            show_chart(ticker)
        else:
            st.warning("No data")

    st.subheader("Watchlist")
    c1, c2 = st.columns([4, 1])
    new_t = c1.text_input("Add", placeholder="Ticker", label_visibility="collapsed").strip().upper()
    if c2.button("Add") and new_t:
        wl = session.setdefault("watchlist", [])
        if new_t not in wl:
            wl.append(new_t)
            save_session(session)
            st.rerun()
    for i, t in enumerate(session.get("watchlist", [])):
        wc1, wc2 = st.columns([6, 1])
        q = get_quote(t)
        if q:
            wc1.write(f"**{t}**  ${q['price']}  ({q['change']:+.2f}%)")
        else:
            wc1.write(t)
        if wc2.button("×", key=f"rm{i}"):
            session["watchlist"].pop(i)
            save_session(session)
            st.rerun()

    st.subheader("Risk")
    rc1, rc2, rc3 = st.columns(3)
    rt = rc1.text_input("Ticker", "NVDA", key="rt").strip().upper()
    risk_amt = rc2.number_input("$ Risk", value=100.0, step=25.0)
    stop_pct = rc3.number_input("Stop %", value=2.0, step=0.5)
    if st.button("Calculate"):
        q = get_quote(rt)
        if q:
            price = q["price"]
            stop = round(price * (1 - stop_pct / 100), 2)
            risk_per = price - stop
            shares = int(risk_amt / risk_per) if risk_per > 0 else 0
            actual = round(shares * risk_per, 2)
            st.write(f"**Entry** ${price}")
            st.write(f"**Stop** ${stop}")
            st.write(f"**Shares** {shares}")
            st.write(f"**Risk** ${actual}")
            st.write(f"**1.5R** ${round(price + risk_per * 1.5, 2)}")
            st.write(f"**2R** ${round(price + risk_per * 2, 2)}")
        else:
            st.warning("No price")

    st.subheader("Notes")
    notes = st.text_area("", session.get("notes", ""), height=90, placeholder="Notes for today")
    if st.button("Save"):
        session["notes"] = notes
        save_session(session)
        st.success("Saved")

def main():
    session = load_session()
    page_main(session)

if __name__ == "__main__":
    main()
