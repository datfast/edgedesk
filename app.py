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
    letter-spacing: -0.02em;
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
.stButton > button:hover {
    background: #1e293b;
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

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist["MA20"], name="MA20", line=dict(color="#f59e0b", width=1.2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist["MA50"], name="MA50", line=dict(color="#3b82f6", width=1.2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist["RSI"], name="RSI", line=dict(color="#8b5cf6")), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", row=2, col=1)
        fig.update_layout(
            height=420,
            margin=dict(l=8, r=8, t=28, b=8),
            xaxis_rangeslider_visible=False,
            showlegend=True,
            title=ticker,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255
