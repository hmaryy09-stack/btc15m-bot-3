import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
import streamlit as st


# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="BTC 15 MIN",
    page_icon="₿",
    layout="centered"
)

NY = ZoneInfo("America/New_York")

SERIES = "KXBTC15M"
REFRESH = 10


# =========================================================
# ESTILO SENCILLO
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #070b14;
    }

    .block-container {
        max-width: 720px;
        padding-top: 1rem;
    }

    h1, h2, h3 {
        color: white;
    }

    .small {
        color: #9aa6b8;
    }

    .big {
        font-size: 42px;
        font-weight: 900;
    }

    .green {
        color: #42ef9a;
    }

    .red {
        color: #ff5961;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# KALSHI
# =========================================================

@st.cache_data(ttl=8)
def get_markets():

    urls = [
        "https://external-api.kalshi.com/trade-api/v2/markets",
        "https://api.elections.kalshi.com/trade-api/v2/markets"
    ]

    for url in urls:
        try:
            r = requests.get(
                url,
                params={
                    "series_ticker": SERIES,
                    "status": "open",
                    "limit": 50
                },
                timeout=8
            )

            if r.ok:
                return r.json().get("markets", [])

        except Exception:
            pass

    return []


def parse_time(value):

    try:

        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(
                value,
                tz=timezone.utc
            )

        value = str(value).replace(
            "Z",
            "+00:00"
        )

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:
        return None


def current_market():

    now = datetime.now(timezone.utc)

    for market in get_markets():

        opened = parse_time(
            market.get("open_time")
        )

        closed = parse_time(
            market.get("close_time")
        )

        if opened and closed:

            if opened <= now < closed:
                return market

    return None


def get_target(market):

    if not market:
        return None

    for key in [
        "custom_strike",
        "strike",
        "floor_strike",
        "cap_strike"
    ]:

        value = market.get(key)

        if value is not None:

            try:
                return float(value)

            except Exception:
                pass

    return None


def get_kalshi_probability(market):

    if not market:
        return None

    try:

        bid = market.get(
            "yes_bid_dollars"
        )

        ask = market.get(
            "yes_ask_dollars"
        )

        last = market.get(
            "last_price_dollars"
        )

        if bid is not None and ask is not None:

            bid = float(bid)
            ask = float(ask)

            return (bid + ask) / 2

        if last is not None:
            return float(last)

    except Exception:
        pass

    return None


# =========================================================
# BITCOIN
# =========================================================

@st.cache_data(ttl=8)
def get_btc_price():

    try:

        r = requests.get(
            "https://api.kraken.com/0/public/Ticker",
            params={"pair": "XBTUSD"},
            timeout=8
        )

        data = r.json()

        result = data.get(
            "result",
            {}
        )

        if result:

            item = next(
                iter(result.values())
            )

            return float(
                item["c"][0]
            )

    except Exception:
        pass

    return None


@st.cache_data(ttl=8)
def get_btc_candles():

    try:

        r = requests.get(
            "https://api.kraken.com/0/public/OHLC",
            params={
                "pair": "XBTUSD",
                "interval": 1
            },
            timeout=8
        )

        data = r.json()

        result = data.get(
            "result",
            {}
        )

        if not result:
            return []

        key = next(
            k for k in result
            if k != "last"
        )

        return [
            {
                "time": int(row[0]),
                "close": float(row[4])
            }
            for row in result[key]
        ]

    except Exception:
        return []


# =========================================================
# SEÑAL
# =========================================================

def calculate_signal(candles):

    if len(candles) < 16:

        return "SUBE", 0.55

    prices = [
        x["close"]
        for x in candles
    ]

    last = prices[-1]

    r1 = (
        last / prices[-2]
    ) - 1

    r3 = (
        last / prices[-4]
    ) - 1

    r5 = (
        last / prices[-6]
    ) - 1

    r10 = (
        last / prices[-11]
    ) - 1

    momentum = (
        r1 * 0.35
        + r3 * 0.30
        + r5 * 0.20
        + r10 * 0.15
    )

    if momentum >= 0:
        direction = "SUBE"
    else:
        direction = "BAJA"

    probability = (
        0.55
        + min(
            0.29,
            abs(momentum) * 700
        )
    )

    return direction, probability


# =========================================================
# DATOS
# =========================================================

market = current_market()

btc = get_btc_price()

candles = get_btc_candles()

target = get_target(market)

kalshi = get_kalshi_probability(
    market
)


# =========================================================
# DIRECCIÓN FIJA POR VELA
# =========================================================

if market:

    open_time = parse_time(
        market.get("open_time")
    )

    close_time = parse_time(
        market.get("close_time")
    )

    candle_id = (
        market.get("ticker"),
        str(open_time)
    )

else:

    open_time = None
    close_time = None

    candle_id = None


if candle_id:

    if st.session_state.get(
        "signal_candle"
    ) != candle_id:

        direction, probability = calculate_signal(
            candles
        )

        st.session_state[
            "signal_candle"
        ] = candle_id

        st.session_state[
            "signal_direction"
        ] = direction

        st.session_state[
            "signal_probability"
        ] = probability

    else:

        direction = st.session_state[
            "signal_direction"
        ]

        probability = st.session_state[
            "signal_probability"
        ]

else:

    direction = "SUBE"
    probability = 0.55


# =========================================================
# ENCABEZADO
# =========================================================

now = datetime.now(NY)

st.title("₿ BTC • 15 MIN")

st.caption(
    f"Predictor • Kalshi   🟢 EN VIVO   "
    f"{now.strftime('%-I:%M:%S %p')}"
)


# =========================================================
# LECTURA ACTUAL
# =========================================================

st.subheader("LECTURA ACTUAL")

if direction == "SUBE":

    st.success(
        f"▲ SUBE — {probability * 100:.0f}%"
    )

else:

    st.error(
        f"▼ BAJA — {probability * 100:.0f}%"
    )

st.write("🔒 Dirección fija durante esta vela.")

if btc:
    st.metric(
        "BTC",
        f"${btc:,.2f}"
    )


# =========================================================
# OBJETIVO Y CIERRE
# =========================================================

col1, col2 = st.columns(2)

with col1:

    st.subheader("🎯 OBJETIVO KALSHI")

    if target:
        st.metric(
            "Objetivo",
            f"${target:,.2f}"
        )
    else:
        st.write("—")


with col2:

    st.subheader("⏱️ CIERRE")

    if close_time:

        seconds = max(
            0,
            int(
                (
                    close_time
                    - datetime.now(timezone.utc)
                ).total_seconds()
            )
        )

        minutes = seconds // 60
        secs = seconds % 60

        st.metric(
            "Tiempo",
            f"{minutes:02d}:{secs:02d}"
        )

        st.caption(
            "Cierre "
            + close_time.astimezone(
                NY
            ).strftime("%-I:%M %p")
        )


# =========================================================
# GUÍA
# =========================================================

st.subheader("📉 GUÍA PARA EL CIERRE")

st.write(
    f"**PROBABLE CIERRE {direction}**"
)

st.write(
    f"Probabilidad estimada: "
    f"**{probability * 100:.0f}%**"
)

if btc and target:

    distance = (
        (btc - target)
        / target
        * 100
    )

    st.write(
        f"Distancia al objetivo: "
        f"**{distance:+.3f}%**"
    )


# =========================================================
# KALSHI EN VIVO
# =========================================================

st.subheader("📊 KALSHI EN VIVO")

if kalshi is not None:

    up = kalshi
    down = 1 - kalshi

    col1, col2 = st.columns(2)

    with col1:
        st.success(
            f"🟢 SUBE {up * 100:.0f}%"
        )

    with col2:
        st.error(
            f"🔴 BAJA {down * 100:.0f}%"
        )

else:

    st.write(
        "Esperando datos de Kalshi..."
    )


# =========================================================
# ENTRADA
# =========================================================

st.subheader("💰 GUÍA DE ENTRADA")

max_entry = (
    probability / 1.10
)

st.metric(
    "Entrada máxima sugerida",
    f"{max_entry * 100:.1f}%"
)

st.write(
    "Posición sugerida: **25%**"
)

st.caption(
    "Solo señales. Sin compras automáticas."
)


# =========================================================
# RADAR
# =========================================================

st.subheader("🚨 RADAR")

if kalshi is not None:

    difference = abs(
        kalshi - probability
    )

    if difference >= 0.15:

        st.warning(
            "⚠️ Kalshi está bastante "
            "separado del modelo."
        )

    elif difference >= 0.08:

        st.info(
            "👀 Hay diferencia entre "
            "el modelo y Kalshi."
        )

    else:

        st.success(
            "✅ Modelo y Kalshi están "
            "relativamente alineados."
        )

else:

    st.info(
        "Esperando lectura de Kalshi."
    )


# =========================================================
# PIE
# =========================================================

st.divider()

st.caption(
    "BTC 15 MIN • Hora de Nueva York • "
    "Señales solamente"
)


# =========================================================
# ACTUALIZACIÓN
# =========================================================

time.sleep(REFRESH)

st.rerun()
