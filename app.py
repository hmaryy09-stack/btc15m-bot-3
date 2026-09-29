import time
from datetime import datetime, timezone

import requests
import streamlit as st


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="BTC 15M Predictor",
    page_icon="₿",
    layout="centered",
)


KALSHI_URL = "https://external-api.kalshi.com/trade-api/v2/markets"
SERIES = "KXBTC15M"


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
<style>

.block-container {
    max-width: 680px;
    padding-top: 1rem;
    padding-left: 0.8rem;
    padding-right: 0.8rem;
    padding-bottom: 2rem;
}

.title {
    text-align: center;
    font-size: 1.6rem;
    font-weight: 800;
    margin-bottom: 3px;
}

.subtitle {
    text-align: center;
    font-size: 0.85rem;
    opacity: 0.65;
    margin-bottom: 15px;
}

.status {
    text-align: center;
    font-size: 0.78rem;
    opacity: 0.7;
    margin-bottom: 12px;
}

.card {
    border: 1px solid rgba(128,128,128,.30);
    border-radius: 15px;
    padding: 14px;
    margin: 10px 0;
}

.signal {
    text-align: center;
    font-size: 2rem;
    font-weight: 900;
    padding: 18px;
    border-radius: 16px;
    margin: 12px 0;
}

.up {
    background: rgba(0,190,90,.12);
    border: 1px solid rgba(0,190,90,.45);
}

.down {
    background: rgba(220,50,50,.12);
    border: 1px solid rgba(220,50,50,.45);
}

.big {
    text-align: center;
    font-size: 2.2rem;
    font-weight: 900;
}

.label {
    font-size: .78rem;
    opacity: .65;
}

.value {
    font-size: 1.1rem;
    font-weight: 700;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# BTC
# ============================================================

def get_btc_price():

    try:

        response = requests.get(
            "https://api.kraken.com/0/public/Ticker",
            params={
                "pair": "XBTUSD"
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        result = data.get(
            "result",
            {}
        )

        if not result:
            return None

        pair = list(result.keys())[0]

        return float(
            result[pair]["c"][0]
        )

    except Exception:

        return None


# ============================================================
# KALSHI
# ============================================================

def get_current_market():

    try:

        response = requests.get(
            KALSHI_URL,
            params={
                "series_ticker": SERIES,
                "status": "open",
                "limit": 100,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        markets = data.get(
            "markets",
            []
        )

        now = datetime.now(
            timezone.utc
        )

        for market in markets:

            open_time = market.get(
                "open_time"
            )

            close_time = market.get(
                "close_time"
            )

            if not open_time or not close_time:
                continue

            try:

                if open_time.endswith("Z"):
                    open_dt = datetime.fromisoformat(
                        open_time[:-1] + "+00:00"
                    )
                else:
                    open_dt = datetime.fromisoformat(
                        open_time
                    )

                if close_time.endswith("Z"):
                    close_dt = datetime.fromisoformat(
                        close_time[:-1] + "+00:00"
                    )
                else:
                    close_dt = datetime.fromisoformat(
                        close_time
                    )

            except Exception:

                continue

            if open_dt <= now < close_dt:

                return market

        return None

    except Exception:

        return None


def get_kalshi_probability(market):

    if not market:
        return None

    bid = market.get(
        "yes_bid_dollars"
    )

    ask = market.get(
        "yes_ask_dollars"
    )

    last = market.get(
        "last_price_dollars"
    )

    try:

        if bid is not None and ask is not None:

            return (
                float(bid)
                + float(ask)
            ) / 2

        if last is not None:

            return float(last)

        if bid is not None:

            return float(bid)

        if ask is not None:

            return float(ask)

    except Exception:

        return None

    return None


def get_target(market):

    if not market:
        return None

    for key in [
        "custom_strike",
        "strike",
        "cap_strike",
        "floor_strike",
    ]:

        value = market.get(key)

        if value is not None:

            try:

                return float(value)

            except Exception:

                pass

    return None


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    """
<div class="title">
    ₿ BTC • 15 MIN
</div>

<div class="subtitle">
    Predictor • Kalshi
</div>

<div class="status">
    🟢 EN VIVO • SEÑALES SOLAMENTE
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DATOS
# ============================================================

btc = get_btc_price()

market = get_current_market()

kalshi_probability = get_kalshi_probability(
    market
)

target = get_target(
    market
)


# ============================================================
# SEÑAL INICIAL
# ============================================================

if btc is not None and target is not None:

    if btc >= target:

        direction = "SUBE"
        probability = 0.65

    else:

        direction = "BAJA"
        probability = 0.65

else:

    direction = "SUBE"
    probability = 0.50


# ============================================================
# SEÑAL
# ============================================================

if direction == "SUBE":

    st.markdown(
        """
<div class="signal up">
    🟢 SUBE
</div>
""",
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
<div class="signal down">
    🔴 BAJA
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# PROBABILIDAD
# ============================================================

st.markdown(
    f"""
<div class="card">

<div class="label">
PROBABILIDAD DEL MODELO
</div>

<div class="big">
{probability * 100:.1f}%
</div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# BTC
# ============================================================

btc_text = (
    f"${btc:,.2f}"
    if btc is not None
    else "—"
)

target_text = (
    f"${target:,.2f}"
    if target is not None
    else "—"
)


st.markdown(
    f"""
<div class="card">

<b>₿ BTC ACTUAL</b>

<br>

<span class="value">
{btc_text}
</span>

<br><br>

<b>🎯 PRECIO OBJETIVO</b>

<br>

<span class="value">
{target_text}
</span>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# KALSHI
# ============================================================

kalshi_text = (
    f"{kalshi_probability * 100:.1f}%"
    if kalshi_probability is not None
    else "—"
)


st.markdown(
    f"""
<div class="card">

<b>📊 KALSHI EN VIVO</b>

<br><br>

<span class="value">
{kalshi_text}
</span>

</div>
""",
    unsafe_allow_html=True,
)


st.caption(
    "Sin compras automáticas • Actualización cada 5 segundos"
)


# ============================================================
# ACTUALIZACIÓN
# ============================================================

time.sleep(5)

st.rerun()
