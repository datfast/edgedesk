import streamlit as st
import yfinance as yf
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json
from pathlib import Path
import pandas as pd
import time

DATA_DIR = Path("edgedesk_data")
DATA_DIR.mkdir(exist_ok=True)

INDICES = ["SPY", "QQQ", "IWM"]
FALLBACK_FOCUS = ["NVDA", "TSLA", "AMD", "AAPL"]

CRYPTO_ALIASES = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "AVAX": "AVAX-USD",
    "SOL": "SOL-USD", "DOGE": "DOGE-USD", "XRP": "XRP-USD",
    "ADA": "ADA-USD", "DOT": "DOT-USD", "LINK": "LINK-USD",
    "MATIC": "MATIC-USD", "SHIB": "SHIB-USD", "LTC": "LTC-USD",
    "BCH": "BCH-USD", "UNI": "UNI-USD", "ATOM": "ATOM-USD",
}

st.set_page_config(page_title="EdgeDesk", page_icon="chart", layout="wide")

st.markdown("""
<style>
.stApp { background: #f8fafc; color: #0f172a; }
.main .block-container { padding-top: 0.8rem; padding-bottom: 1.5rem; max-width: 760px; }
h1 { font-size: 1.55rem; font-weight: 700; margin-bottom: 0.1rem; }
h2 { font-size: 1.1rem; font-weight: 600; margin-top: 1.2rem; margin-bottom: 0.4rem; color: #0f172a; }
[data-testid="stMetric"] {
    background: #ffffff; border-radius: 10px; padding: 10px 12px;
    border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
[data-testid="stMetricValue"] { font-size: 1.1rem; font-weight: 600; }
.stButton > button {
    border-radius: 7px; font-weight: 500; background: #1e293b; color: white;
    border: none; padding: 0.3rem 0.8rem;
}
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox > div > div {
    border-radius: 7px; border: 1px solid #cbd5e1;
}
.stPlotlyChart { border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def load_session():
    try:
        path = DATA_DIR / f"session_{today_str()}.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                data.setdefault("alerts", [])
                return data
    except Exception:
        pass
    return {"date": today_str(), "watchlist": [], "notes": "", "alerts": []}

def save_session(session):
    try:
        path = DATA_DIR / f"session_{today_str()}.json"
        with open(path, "w") as f:
            json.dump(session, f, indent=2)
    except Exception:
        pass

def resolve_ticker(ticker):
    t = ticker.upper().strip()
    return CRYPTO_ALIASES.get(t, t)

def get_quote(ticker):
    try:
        resolved = resolve_ticker(ticker)
        hist = yf.Ticker(resolved).history(period="2d")
        if hist.empty and resolved == ticker.upper().strip() and "-" not in resolved:
            crypto_try = f"{resolved}-USD"
            hist = yf.Ticker(crypto_try).history(period="2d")
            if not hist.empty:
                resolved = crypto_try
        if hist.empty:
            return None
        price = round(float(hist["Close"].iloc[-1]), 2)
        change = 0.0
        if len(hist) > 1:
            prev = float(hist["Close"].iloc[-2])
            change = round((price - prev) / prev * 100, 2)
        return {"price": price, "change": change, "ticker": resolved}
    except Exception:
        return None

def get_company_info(ticker):
    try:
        info = yf.Ticker(ticker).info or {}
        name = info.get("shortName") or info.get("longName") or ticker
        summary = info.get("longBusinessSummary") or info.get("description") or ""
        sector = info.get("sector") or ""
        industry = info.get("industry") or ""
        if summary and len(summary) > 280:
            summary = summary[:277] + "..."
        return {"name": name, "summary": summary, "sector": sector, "industry": industry}
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

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_cross = "bullish" if macd_line.iloc[-1] > signal_line.iloc[-1] else "bearish"

        notes = []
        bias = "Neutral"
        lean = "No clear lean"

        if price > ma20 and price > ma50:
            notes.append("Price above both MAs")
            bias = "Bullish"
            lean = "Lean long"
        elif price < ma20 and price < ma50:
            notes.append("Price below both MAs")
            bias = "Bearish"
            lean = "Lean short"
        else:
            notes.append("Price mixed vs MAs")

        if rsi < 30:
            notes.append("RSI oversold zone")
            if bias == "Neutral":
                bias = "Bullish"
                lean = "Lean long"
        elif rsi > 70:
            notes.append("RSI overbought zone")
            if bias == "Neutral":
                bias = "Bearish"
                lean = "Lean short"
        else:
            notes.append(f"RSI {round(rsi, 1)}")

        if macd_cross == "bullish":
            notes.append("MACD above signal")
            if bias == "Neutral":
                bias = "Bullish"
                lean = "Lean long"
        else:
            notes.append("MACD below signal")
            if bias == "Neutral":
                bias = "Bearish"
                lean = "Lean short"

        return {"bias": bias, "notes": notes, "lean": lean}
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

        ema12 = hist["Close"].ewm(span=12, adjust=False).mean()
        ema26 = hist["Close"].ewm(span=26, adjust=False).mean()
        hist["MACD"] = ema12 - ema26
        hist["Signal"] = hist["MACD"].ewm(span=9, adjust=False).mean()
        hist["Histogram"] = hist["MACD"] - hist["Signal"]

        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.55, 0.22, 0.23]
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
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.08)", line_width=0, row=2, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor="rgba(34,197,94,0.08)", line_width=0, row=2, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["MACD"],
            name="MACD", line=dict(color="#0ea5e9", width=1.4)
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["Signal"],
            name="Signal", line=dict(color="#f97316", width=1.2)
        ), row=3, col=1)
        colors = ["#22c55e" if v >= 0 else "#ef4444" for v in hist["Histogram"]]
        fig.add_trace(go.Bar(
            x=hist.index, y=hist["Histogram"],
            name="Histogram", marker_color=colors
        ), row=3, col=1)
        fig.update_layout(
            height=520,
            margin=dict(l=8, r=8, t=28, b=8),
            xaxis_rangeslider_visible=False,
            showlegend=True,
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            title=dict(text=ticker, font=dict(size=14))
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.caption("Chart unavailable")

def get_focus_tickers():
    try:
        r = requests.get("https://api.stocktwits.com/api/2/trending/symbols.json", timeout=5)
        if r.status_code == 200:
            symbols = r.json().get("symbols", [])[:4]
            tickers = [s.get("symbol") for s in symbols if s.get("symbol")]
            if tickers:
                return tickers
    except Exception:
        pass
    return FALLBACK_FOCUS

def get_stocktwits_trending():
    try:
        r = requests.get("https://api.stocktwits.com/api/2/trending/symbols.json", timeout=5)
        if r.status_code != 200:
            return []
        out = []
        for s in r.json().get("symbols", [])[:5]:
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

def get_macro_events(limit=5):
    try:
        cals = yf.Calendars()
        df = cals.get_economic_events_calendar(limit=60)
        if df is None or df.empty:
            return []
        high_keywords = ["CPI", "PPI", "NFP", "Nonfarm", "Payroll", "FOMC", "Fed", "Interest Rate", "GDP", "Retail Sales", "Unemployment", "Jobless", "ISM", "PMI"]
        def is_high(name):
            return any(k.upper() in str(name).upper() for k in high_keywords)
        us = df[df["Region"].astype(str).str.upper().isin(["US", "UNITED STATES"])]
        high = us[us.index.to_series().apply(is_high)]
        source = high if not high.empty else (us if not us.empty else df)
        events = []
        for name, row in source.head(limit).iterrows():
            time_str = str(row.get("Event Time", ""))[:16].replace("T", " ") if row.get("Event Time") else ""
            events.append({
                "name": str(name).replace("*", ""),
                "time": time_str,
                "region": str(row.get("Region", "")),
            })
        return events
    except Exception:
        return []

def check_alerts(session):
    triggered = []
    for a in session.get("alerts", []):
        q = get_quote(a.get("ticker", ""))
        if not q or a.get("target") is None:
            continue
        price = q["price"]
        direction = a.get("direction", "above")
        hit = (direction == "above" and price >= a["target"]) or (direction == "below" and price <= a["target"])
        if hit:
            triggered.append({"ticker": q.get("ticker", a["ticker"]), "price": price, "target": a["target"], "direction": direction})
    return triggered

def broker_links(ticker):
    clean = ticker.replace("-USD", "").upper()
    is_crypto = "-USD" in ticker.upper() or clean in CRYPTO_ALIASES
    links = []
    if not is_crypto:
        links.append(f"[Robinhood](https://robinhood.com/stocks/{clean})")
        links.append("[E*TRADE](https://us.etrade.com/home)")
    links.append(f"[Coinbase](https://www.coinbase.com/price/{clean.lower()})")
    return " · ".join(links)

def calc_levels(ticker, price, direction="long"):
    try:
        hist = yf.Ticker(ticker).history(period="1mo")
        if len(hist) < 14:
            stop_pct = 2.0
        else:
            high = hist["High"]
            low = hist["Low"]
            close = hist["Close"]
            tr = pd.DataFrame({
                "hl": high - low,
                "hc": (high - close.shift()).abs(),
                "lc": (low - close.shift()).abs()
            }).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            stop_pct = round((atr / price) * 100 * 1.5, 1)
            if stop_pct < 1.0:
                stop_pct = 1.0
            if stop_pct > 5.0:
                stop_pct = 5.0
        if direction == "long":
            stop_price = round(price * (1 - stop_pct / 100), 2)
            risk_per = price - stop_price
            tp15 = round(price + risk_per * 1.5, 2)
            tp2 = round(price + risk_per * 2, 2)
        else:
            stop_price = round(price * (1 + stop_pct / 100), 2)
            risk_per = stop_price - price
            tp15 = round(price - risk_per * 1.5, 2)
            tp2 = round(price - risk_per * 2, 2)
        return {
            "stop": stop_price,
            "stop_pct": stop_pct,
            "tp15": tp15,
            "tp2": tp2
        }
    except Exception:
        if direction == "long":
            stop_price = round(price * 0.98, 2)
            risk_per = price - stop_price
            return {
                "stop": stop_price,
                "stop_pct": 2.0,
                "tp15": round(price + risk_per * 1.5, 2),
                "tp2": round(price + risk_per * 2, 2)
            }
        else:
            stop_price = round(price * 1.02, 2)
            risk_per = stop_price - price
            return {
                "stop": stop_price,
                "stop_pct": 2.0,
                "tp15": round(price - risk_per * 1.5, 2),
                "tp2": round(price - risk_per * 2, 2)
            }

def get_ideas(lean_type="Lean long", limit=5):
    watch = ["NVDA", "TSLA", "AMD", "AAPL", "META", "AMZN", "MSFT", "GOOGL", "AVGO", "NFLX"]
    ideas = []
    direction = "long" if lean_type == "Lean long" else "short"
    for t in watch:
        bias = get_technical_bias(t)
        if bias and bias.get("lean") == lean_type:
            q = get_quote(t)
            if not q:
                continue
            levels = calc_levels(t, q["price"], direction)
            ideas.append({
                "ticker": t,
                "price": q["price"],
                "change": q["change"],
                **levels
            })
        if len(ideas) >= limit:
            break
    return ideas

def page_main(session):
    st.title("EdgeDesk")

    with st.sidebar:
        st.header("Guide")
        st.subheader("RSI")
        st.write("Relative Strength Index. A momentum reading from 0 to 100.")
        st.caption("Above 70: often overbought")
        st.caption("Below 30: often oversold")
        st.caption("Around 50: neutral")
        st.caption("Used as one check for the bias and lean. Not a signal by itself.")
        st.subheader("MACD")
        st.write("Moving Average Convergence Divergence.")
        st.caption("MACD above signal: bullish momentum")
        st.caption("MACD below signal: bearish momentum")
        st.caption("Histogram shows strength of the move.")
        st.divider()
        auto = st.checkbox("Auto-refresh (2 min)", key="auto_refresh")

    if auto:
        time.sleep(120)
        st.rerun()

    st.subheader("Macro")
    events = get_macro_events()
    if events:
        for e in events:
            st.write(f"**{e['name']}**" + (f" · {e['time']}" if e['time'] else "") + (f" ({e['region']})" if e['region'] else ""))
    else:
        st.caption("Unavailable")

    st.subheader("Alerts")
    triggered = check_alerts(session)
    if triggered:
        for t in triggered:
            st.success(f"**{t['ticker']}** ${t['price']} ({t['direction']} ${t['target']})")
    else:
        st.caption("None triggered")

    with st.expander("Set alert"):
        ac1, ac2, ac3 = st.columns([2, 1.5, 1.5])
        at = ac1.text_input("Ticker", key="alert_t", placeholder="AVAX").strip().upper()
        adir = ac2.selectbox("Dir", ["above", "below"], key="alert_dir", label_visibility="collapsed")
        atarget = ac3.number_input("Target", min_value=0.0, value=0.0, step=0.01, key="alert_target", label_visibility="collapsed")
        if st.button("Add Alert", key="add_alert") and at and atarget > 0:
            session.setdefault("alerts", []).append({"ticker": at, "target": atarget, "direction": adir})
            save_session(session)
            st.rerun()

    for i, a in enumerate(session.get("alerts", [])):
        c1, c2 = st.columns([6, 1])
        c1.caption(f"{a['ticker']} {a['direction']} ${a['target']}")
        if c2.button("x", key=f"alert_rm{i}"):
            session["alerts"].pop(i)
            save_session(session)
            st.rerun()

    st.subheader("Market")
    cols = st.columns(3)
    for i, t in enumerate(INDICES):
        q = get_quote(t)
        cols[i].metric(t, f"${q['price']}" if q else "-", f"{q['change']:+.2f}%" if q else None)

    st.subheader("Focus")
    focus = get_focus_tickers()
    fcols = st.columns(len(focus))
    for i, t in enumerate(focus):
        q = get_quote(t)
        fcols[i].metric(t, f"${q['price']}" if q else "-", f"{q['change']:+.2f}%" if q else None)

    st.subheader("Long Ideas")
    long_ideas = get_ideas("Lean long")
    if long_ideas:
        for idx, item in enumerate(long_ideas):
            with st.container():
                c1, c2, c3 = st.columns([2, 3, 1])
                c1.metric(item["ticker"], f"${item['price']}", f"{item['change']:+.2f}%")
                c2.caption("Lean long")
                c2.caption(f"Stop ${item['stop']} ({item['stop_pct']}%)")
                c2.caption(f"1.5R ${item['tp15']} · 2R ${item['tp2']}")
                if c3.button("Add", key=f"add_long_{idx}"):
                    wl = session.setdefault("watchlist", [])
                    if item["ticker"] not in wl:
                        wl.append(item["ticker"])
                        save_session(session)
                        st.rerun()
    else:
        st.caption("None right now")

    st.subheader("Short Ideas")
    short_ideas = get_ideas("Lean short")
    if short_ideas:
        for idx, item in enumerate(short_ideas):
            with st.container():
                c1, c2, c3 = st.columns([2, 3, 1])
                c1.metric(item["ticker"], f"${item['price']}", f"{item['change']:+.2f}%")
                c2.caption("Lean short")
                c2.caption(f"Stop ${item['stop']} ({item['stop_pct']}%)")
                c2.caption(f"1.5R ${item['tp15']} · 2R ${item['tp2']}")
                if c3.button("Add", key=f"add_short_{idx}"):
                    wl = session.setdefault("watchlist", [])
                    if item["ticker"] not in wl:
                        wl.append(item["ticker"])
                        save_session(session)
                        st.rerun()
    else:
        st.caption("None right now")

    st.subheader("Trending")
    trending = get_stocktwits_trending()
    if trending:
        tcols = st.columns(len(trending))
        for i, item in enumerate(trending):
            tcols[i].markdown(f"**{item['ticker']}**\n{item['sentiment']}")
    else:
        st.caption("Unavailable")

    st.subheader("Chart")
    ticker = st.text_input("Ticker", placeholder="NVDA, AVAX").strip().upper()
    if ticker:
        q = get_quote(ticker)
        if q:
            display = q.get("ticker", ticker)
            st.metric(display, f"${q['price']}", f"{q['change']:+.2f}%")
            info = get_company_info(display)
            if info:
                st.write(f"**{info['name']}**")
                if info["sector"] or info["industry"]:
                    st.caption(f"{info['sector']} · {info['industry']}".strip(" ·"))
                if info["summary"]:
                    st.caption(info["summary"])
            bias = get_technical_bias(display)
            if bias:
                st.write(f"**Bias:** {bias['bias']}")
                st.write(f"**Lean:** {bias['lean']}")
                for n in bias["notes"]:
                    st.caption(n)
            direction = "long" if bias and bias.get("lean") == "Lean long" else "short"
            levels = calc_levels(display, q["price"], direction)
            st.caption(f"Stop ${levels['stop']} ({levels['stop_pct']}%) · 1.5R ${levels['tp15']} · 2R ${levels['tp2']}")
            show_chart(display)
            st.markdown("**Trade**  " + broker_links(display))
        else:
            st.warning("No data")

    st.subheader("Watchlist")
    c1, c2 = st.columns([4, 1])
    new_t = c1.text_input("Add", placeholder="Ticker", label_visibility="collapsed").strip().upper()
    if c2.button("Add", key="add_watch") and new_t:
        wl = session.setdefault("watchlist", [])
        if new_t not in wl:
            wl.append(new_t)
            save_session(session)
            st.rerun()
    for i, t in enumerate(session.get("watchlist", [])):
        wc1, wc2 = st.columns([6, 1])
        q = get_quote(t)
        if q:
            wc1.write(f"**{q.get('ticker', t)}**  ${q['price']}  ({q['change']:+.2f}%)")
        else:
            wc1.write(t)
        if wc2.button("x", key=f"rm{i}"):
            session["watchlist"].pop(i)
            save_session(session)
            st.rerun()

    st.subheader("Risk")
    rc1, rc2, rc3 = st.columns(3)
    rt = rc1.text_input("Ticker", "NVDA", key="rt").strip().upper()
    risk_amt = rc2.number_input("$ Risk", value=100.0, step=25.0)
    stop_pct = rc3.number_input("Stop %", value=2.0, step=0.5)
    if st.button("Calculate", key="calc_risk"):
        q = get_quote(rt)
        if q:
            price = q["price"]
            stop = round(price * (1 - stop_pct / 100), 2)
            risk_per = price - stop
            shares = int(risk_amt / risk_per) if risk_per > 0 else 0
            actual = round(shares * risk_per, 2)
            st.write(f"**Entry** ${price} · **Stop** ${stop}")
            st.write(f"**Shares** {shares} · **Risk** ${actual}")
            st.write(f"**1.5R** ${round(price + risk_per * 1.5, 2)} · **2R** ${round(price + risk_per * 2, 2)}")
        else:
            st.warning("No price")

    st.subheader("Notes")
    notes = st.text_area("", session.get("notes", ""), height=80, placeholder="Notes")
    if st.button("Save", key="save_notes"):
        session["notes"] = notes
        save_session(session)
        st.success("Saved")

def main():
    session = load_session()
    page_main(session)

if __name__ == "__main__":
    main()
