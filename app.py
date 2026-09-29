import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
import streamlit as st

st.set_page_config(page_title="BTC 15 MIN", page_icon="₿", layout="centered")

NY = ZoneInfo("America/New_York")
SERIES = "KXBTC15M"
REFRESH = 10

st.markdown("""
<style>
.stApp { background:#070b14; }
.block-container { max-width:720px; padding-top:1rem; }
h1,h2,h3 { color:white; }
.fixed { border:1px solid #334155; border-radius:12px; padding:12px; background:#0b1220; }
.live { border:1px solid #26354d; border-radius:12px; padding:12px; background:#0a101c; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# KALSHI
# =========================================================

@st.cache_data(ttl=8)
def get_markets():
    urls = [
        "https://external-api.kalshi.com/trade-api/v2/markets",
        "https://api.elections.kalshi.com/trade-api/v2/markets",
    ]
    for url in urls:
        try:
            r = requests.get(
                url,
                params={"series_ticker": SERIES, "status": "open", "limit": 50},
                timeout=8,
            )
            if r.ok:
                return r.json().get("markets", [])
        except Exception:
            pass
    return []


def parse_time(value):
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        value = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def current_market():
    now = datetime.now(timezone.utc)
    for market in get_markets():
        opened = parse_time(market.get("open_time"))
        closed = parse_time(market.get("close_time"))
        if opened and closed and opened <= now < closed:
            return market
    return None


def get_target(market):
    if not market:
        return None
    for key in ("custom_strike", "strike", "floor_strike", "cap_strike"):
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
        bid = market.get("yes_bid_dollars")
        ask = market.get("yes_ask_dollars")
        last = market.get("last_price_dollars")

        if bid is not None and ask is not None:
            return (float(bid) + float(ask)) / 2

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
            timeout=8,
        )
        result = r.json().get("result", {})
        if result:
            item = next(iter(result.values()))
            return float(item["c"][0])
    except Exception:
        pass
    return None


@st.cache_data(ttl=8)
def get_btc_candles():
    try:
        r = requests.get(
            "https://api.kraken.com/0/public/OHLC",
            params={"pair": "XBTUSD", "interval": 1},
            timeout=8,
        )
        result = r.json().get("result", {})
        if not result:
            return []

        key = next(k for k in result if k != "last")

        return [
            {"time": int(row[0]), "close": float(row[4])}
            for row in result[key]
        ]
    except Exception:
        return []


# =========================================================
# MODELO
# =========================================================

def calculate_signal(candles):
    if len(candles) < 16:
        return "SUBE", 0.55

    prices = [x["close"] for x in candles]
    last = prices[-1]

    r1 = last / prices[-2] - 1
    r3 = last / prices[-4] - 1
    r5 = last / prices[-6] - 1
    r10 = last / prices[-11] - 1

    momentum = (
        r1 * 0.35
        + r3 * 0.30
        + r5 * 0.20
        + r10 * 0.15
    )

    direction = "SUBE" if momentum >= 0 else "BAJA"

    probability = 0.55 + min(0.29, abs(momentum) * 700)

    return direction, probability


# =========================================================
# SEÑAL PRINCIPAL FIJA
# =========================================================

@st.cache_data(ttl=3600)
def fixed_signal(ticker, open_time_key):
    direction, probability = calculate_signal(get_btc_candles())
    return direction, probability


# =========================================================
# DATOS ACTUALES
# =========================================================

market = current_market()
btc = get_btc_price()
target = get_target(market)
kalshi = get_kalshi_probability(market)

if market:
    open_time = parse_time(market.get("open_time"))
    close_time = parse_time(market.get("close_time"))
    ticker = market.get("ticker")
else:
    open_time = None
    close_time = None
    ticker = None

if ticker and open_time:
    direction, probability = fixed_signal(
        ticker,
        str(int(open_time.timestamp())),
    )
else:
    direction, probability = "SUBE", 0.55

now = datetime.now(NY)
# =========================================================
# LECTURA PRINCIPAL FIJA
# =========================================================

st.subheader("🔒 LECTURA ACTUAL — FIJA")

st.markdown(
    '<div class="fixed"><b>SEÑAL DEL MODELO</b><br>'
    'Esta dirección permanece fija durante toda la vela.</div>',
    unsafe_allow_html=True,
)

if direction == "SUBE":
    st.success(f"▲ SUBE — {probability * 100:.0f}%")
else:
    st.error(f"▼ BAJA — {probability * 100:.0f}%")

st.write(
    "🔒 La dirección NO cambia hasta que termine "
    "la vela de 15 minutos."
)

if btc:
    st.metric("BTC", f"${btc:,.2f}")


# =========================================================
# OBJETIVO Y CIERRE
# =========================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 OBJETIVO KALSHI")

    st.metric(
        "Objetivo",
        f"${target:,.2f}" if target else "—"
    )

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
            ),
        )

        st.metric(
            "Tiempo",
            f"{seconds // 60:02d}:{seconds % 60:02d}"
        )

        st.caption(
            "Cierre "
            + close_time.astimezone(NY).strftime("%-I:%M %p")
        )

    else:
        st.write("—")


# =========================================================
# GUÍA PARA EL CIERRE
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

st.markdown(
    '<div class="live"><b>LECTURA DEL MERCADO</b><br>'
    'Esta parte SÍ puede subir o bajar durante la misma vela. '
    'No cambia la dirección fija del modelo.</div>',
    unsafe_allow_html=True,
)

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
# MODELO VS KALSHI
# =========================================================

st.subheader("🔎 MODELO VS KALSHI")

if kalshi is not None:

    kalshi_side = (
        kalshi
        if direction == "SUBE"
        else 1 - kalshi
    )

    st.write(
        f"Señal fija del modelo: "
        f"**{direction} {probability * 100:.0f}%**"
    )

    st.write(
        f"Kalshi a favor de la señal: "
        f"**{kalshi_side * 100:.0f}%**"
    )

else:

    st.write(
        "Esperando lectura de Kalshi..."
    )


# =========================================================
# GUÍA DE ENTRADA
# =========================================================

st.subheader("💰 GUÍA DE ENTRADA")

max_entry = probability / 1.10

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

    kalshi_side = (
        kalshi
        if direction == "SUBE"
        else 1 - kalshi
    )

    difference = abs(
        kalshi_side - probability
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
# ESTADO DE LA VELA
# =========================================================

st.subheader("🔐 ESTADO DE LA VELA")

if ticker and close_time:

    st.write(
        f"Ticker: **{ticker}**"
    )

    st.write(
        f"Dirección bloqueada: **{direction}**"
    )

    st.write(
        "La dirección se renovará únicamente "
        "cuando comience una nueva vela "
        "de 15 minutos."
    )

else:

    st.write(
        "Esperando una vela activa de Kalshi..."
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



# =========================================================
# ENCABEZADO
# =========================================================

st.title("₿ BTC • 15 MIN")
st.caption(
    f"Predictor • Kalshi   🟢 EN VIVO   {now.strftime('%-I:%M:%S %p')}"
)
