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

def get_price
