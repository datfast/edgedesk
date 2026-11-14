import streamlit as st
import yfinance as yf
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
.stApp { background: #f8fafc; color: #1e293b; }
.main .block-container { padding-top: 1.5rem; max-width: 1000px; }
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

    st.subheader("Look up stock")
    ticker = st.text_input("Ticker").upper()
    if ticker:
        price = get_price(ticker)
        if price:
            st.metric(ticker, f"${price}")
        else:
            st.warning("No data")

    st.subheader("Watchlist")
    new_ticker = st.text_input("Add to watchlist").upper()
    if st.button("Add") and new_ticker:
        session.setdefault("watchlist", []).append(new_ticker)
        save_session(session)
        st.rerun()
    
    for i, t in enumerate(session.get("watchlist", [])):
        col1, col2 = st.columns([3, 1])
        col1.write(t)
        if col2.button("Remove", key=f"rm{i}"):
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
            stop = round(price * (1 - stop_pct/100), 2)
            shares = int(risk_amount / (price - stop)) if price > stop else 0
            st.write(f"Price: ${price}")
            st.write(f"Stop: ${stop}")
            st.write(f"Shares: {shares}")
        else:
            st.warning("No price")

    st.subheader("Trade")
    st.markdown("[Robinhood](https://robinhood.com) • [Coinbase](https://www.coinbase.com)")

def page_news():
    st.header("News")
    ticker = st.text_input("Ticker for news", "NVDA").upper()
    if st.button("Get News"):
        try:
            news = yf.Ticker(ticker).news
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
    st.write("**Day Trading** — Same day trades, tight stops.")
    st.write("**Swing Trading** — Hold days to weeks.")
    st.write("**Liquidity Sweep** — Sweep of a level then structure shift.")
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
