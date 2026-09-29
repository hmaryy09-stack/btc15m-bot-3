import time
import math
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

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

NY = ZoneInfo("America/New_York")

SERIES = "KXBTC15M"
REFRESH_SECONDS = 10
PREVIEW_SECONDS = 180
MIN_EXPECTED_RETURN = 0.10
SUGGESTED_POSITION = 25

KALSHI_HOSTS = [
    "https://external-api.kalshi.com/trade-api/v2",
    "https://api.elections.kalshi.com/trade-api/v2",
]


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at top, #101827 0%, #070b14 42%, #05070d 100%);
        color: #f5f7fb;
    }

    .block-container {
        max-width: 760px;
        padding: 1rem 0.75rem 3rem 0.75rem;
    }

    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .btc-icon {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: #f7931a;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 30px;
        font-weight: 900;
        box-shadow: 0 0 18px rgba(247,147,26,.22);
    }

    .title {
        font-size: 25px;
        font-weight: 850;
        line-height: 1.05;
    }

    .subtitle {
        color: #8f9aad;
        font-size: 15px;
        margin-top: 4px;
    }

    .live {
        text-align: right;
        color: #39e58c;
        font-size: 14px;
        font-weight: 800;
        line-height: 1.2;
    }

    .live-dot {
        display: inline-block;
        width: 11px;
        height: 11px;
        border-radius: 50%;
        background: #21e779;
        margin-right: 5px;
        box-shadow: 0 0 12px rgba(33,231,121,.7);
    }

    .card {
        background: linear-gradient(145deg, #111a2a, #0b111d);
        border: 1px solid #263653;
        border-radius: 23px;
        padding: 18px;
        margin: 12px 0;
        box-shadow: 0 10px 35px rgba(0,0,0,.22);
    }

    .main-card {
        padding: 20px;
    }

    .section-title {
        color: #aeb9cb;
        font-size: 15px;
        font-weight: 800;
        letter-spacing: .2px;
        margin-bottom: 10px;
    }

    .signal-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 15px;
    }

    .signal {
        font-size: 43px;
        font-weight: 900;
        line-height: 1;
        letter-spacing: -1px;
    }

    .signal-up {
        color: #42ef9a;
    }

    .signal-down {
        color: #ff5961;
    }

    .prob {
        text-align: right;
    }

    .prob-number {
        font-size: 46px;
        line-height: 1;
        font-weight: 900;
        color: #48ee9b;
    }

    .prob-label {
        color: #8d99ab;
        font-size: 14px;
        margin-top: 5px;
    }

    .locked {
        color: #9ca8ba;
        font-size: 14px;
        margin-top: 9px;
    }

    .price {
        font-size: 31px;
        font-weight: 850;
        margin-top: 15px;
    }

    .change-up {
        color: #45e995;
        font-size: 16px;
        font-weight: 700;
    }

    .change-down {
        color: #ff5a63;
        font-size: 16px;
        font-weight: 700;
    }

    .confirm-title {
        margin-top: 22px;
        font-size: 16px;
        font-weight: 800;
        color: #dbe2ec;
    }

    .bars {
        display: flex;
        gap: 9px;
        margin-top: 10px;
    }

    .bar {
        height: 14px;
        flex: 1;
        border-radius: 12px;
        background: #26334a;
    }

    .bar.active {
        background: #42e995;
        box-shadow: 0 0 9px rgba(66,233,149,.18);
    }

    .notice {
        margin-top: 16px;
        background: #14243b;
        border-radius: 16px;
        padding: 13px 15px;
    }

    .notice-title {
        font-size: 16px;
        font-weight: 850;
        color: #e5ebf4;
    }

    .notice-text {
        color: #8996aa;
        font-size: 14px;
        margin-top: 4px;
    }

    .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    .small-card {
        background: linear-gradient(145deg, #111a2a, #0b111d);
        border: 1px solid #263653;
        border-radius: 20px;
        padding: 16px;
        min-height: 126px;
    }

    .small-title {
        color: #aeb9cb;
        font-size: 14px;
        font-weight: 800;
    }

    .small-value {
        font-size: 25px;
        font-weight: 900;
        margin-top: 12px;
    }

    .small-sub {
        color: #8b97a9;
        font-size: 13px;
        margin-top: 4px;
    }

    .guide {
        border-color: #3b3444;
    }

    .guide-up {
        color: #42ef9a;
    }

    .guide-down {
        color: #ff5961;
    }

    .guide-title {
        font-size: 29px;
        font-weight: 900;
        margin-top: 4px;
    }

    .guide-text {
        color: #8996aa;
        font-size: 14px;
        margin-top: 4px;
        line-height: 1.35;
    }

    .metrics {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 8px;
        margin-top: 14px;
    }

    .metric {
        background: #0b1422;
        border: 1px solid #243550;
        border-radius: 14px;
        padding: 10px 7px;
        text-align: center;
    }

    .metric-label {
        color: #77859a;
        font-size: 11px;
        text-transform: uppercase;
    }

    .metric-value {
        color: #e8edf5;
        font-size: 15px;
        font-weight: 850;
        margin-top: 5px;
    }

    .kalshi-title {
        color: #b6c1d1;
        font-size: 16px;
        font-weight: 850;
    }

    .kalshi-row {
        display: flex;
        justify-content: space-between;
        margin-top: 13px;
        font-size: 21px;
        font-weight: 850;
    }

    .green {
        color: #42ef9a;
    }

    .red {
        color: #ff5961;
    }

    .live-bar {
        display: flex;
        height: 15px;
        border-radius: 20px;
        overflow: hidden;
        background: #27354b;
        margin-top: 12px;
    }

    .live-up {
        background: #35d985;
    }

    .live-down {
        background: #f2555d;
    }

    .entry {
        border-color: #29415e;
    }

    .entry-title {
        color: #b7c2d3;
        font-size: 15px;
        font-weight: 850;
    }

    .entry-number {
        font-size: 28px;
        font-weight: 900;
        margin-top: 8px;
    }

    .entry-sub {
        color: #8996aa;
        font-size: 13px;
        margin-top: 4px;
    }

    .radar {
        border-color: #443b2a;
    }

    .radar-title {
        color: #f1c866;
        font-size: 16px;
        font-weight: 900;
    }

    .radar-text {
        color: #a3adbc;
        font-size: 14px;
        margin-top: 7px;
        line-height: 1.4;
    }

    .preview {
        border-color: #32415b;
        background: linear-gradient(145deg, #101a2b, #0a101b);
    }

    .preview-title {
        color: #8da2be;
        font-size: 14px;
        font-weight: 850;
    }

    .preview-value {
        font-size: 22px;
        font-weight: 900;
        margin-top: 5px;
    }

    .footer {
        text-align: center;
        color: #68758a;
        font-size: 12px;
        margin-top: 18px;
    }

    @media (max-width: 520px) {
        .block-container {
            padding-left: .55rem;
            padding-right: .55rem;
        }

        .signal {
            font-size: 38px;
        }

        .prob-number {
            font-size: 39px;
        }

        .price {
            font-size: 27px;
        }

        .guide-title {
            font-size: 24px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FUNCIONES
# ============================================================

def kalshi_get(path, params=None):
    for host in KALSHI_HOSTS:
        try:
            r = requests.get(
                host + path,
                params=params,
                timeout=8,
                headers={"User-Agent": "BTC15M-Predictor/1.0"},
            )
            if r.ok:
                return r.json()
        except Exception:
            pass

    return None


@st.cache_data(ttl=8)
def get_btc_price():
    try:
        r = requests.get(
            "https://api.kraken.com/0/public/Ticker",
            params={"pair": "XBTUSD"},
            timeout=8,
        )
        data = r.json()
        result = data.get("result", {})

        if result:
            item = next(iter(result.values()))
            return float(item["c"][0])

    except Exception:
        pass

    return None


@st.cache_data(ttl=8)
def get_btc_ohlc():
    try:
        r = requests.get(
            "https://api.kraken.com/0/public/OHLC",
            params={
                "pair": "XBTUSD",
                "interval": 1,
            },
            timeout=8,
        )

        data = r.json()
        result = data.get("result", {})

        if not result:
            return []

        key = next(k for k in result.keys() if k != "last")
        rows = result[key]

        candles = []

        for row in rows:
            candles.append(
                {
                    "ts": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                }
            )

        return candles

    except Exception:
        return []


def parse_dt(value):
    if not value:
        return None

    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)

        text = str(value).replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


@st.cache_data(ttl=8)
def get_markets():
    data = kalshi_get(
        "/markets",
        {
            "series_ticker": SERIES,
            "status": "open",
            "limit": 50,
        },
    )

    if not data:
        return []

    return data.get("markets", [])


def get_current_market():
    markets = get_markets()

    now = datetime.now(timezone.utc)

    valid = []

    for m in markets:
        open_dt = parse_dt(m.get("open_time"))
        close_dt = parse_dt(m.get("close_time"))

        if not open_dt or not close_dt:
            continue

        if open_dt <= now < close_dt:
            valid.append((open_dt, close_dt, m))

    if not valid:
        return None

    valid.sort(key=lambda x: x[0])

    return valid[0][2]


def get_next_market():
    markets = get_markets()

    now = datetime.now(timezone.utc)

    upcoming = []

    for m in markets:
        open_dt = parse_dt(m.get("open_time"))

        if open_dt and open_dt > now:
            upcoming.append((open_dt, m))

    if not upcoming:
        return None

    upcoming.sort(key=lambda x: x[0])

    return upcoming[0][1]


def get_market_target(market):
    if not market:
        return None

    for key in [
        "custom_strike",
        "strike",
        "floor_strike",
        "cap_strike",
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

    values = []

    for key in [
        "yes_bid_dollars",
        "yes_ask_dollars",
        "last_price_dollars",
    ]:
        value = market.get(key)

        if value is not None:
            try:
                values.append(float(value))
            except Exception:
                pass

    if not values:
        return None

    # La lectura principal usa el punto medio bid/ask cuando ambos existen.
    if (
        market.get("yes_bid_dollars") is not None
        and market.get("yes_ask_dollars") is not None
    ):
        try:
            bid = float(market["yes_bid_dollars"])
            ask = float(market["yes_ask_dollars"])

            if 0 <= bid <= 1 and 0 <= ask <= 1:
                return (bid + ask) / 2
        except Exception:
            pass

    return max(0.0, min(1.0, values[-1]))


def get_historical_before_open(open_dt):
    candles = get_btc_ohlc()

    if not candles or not open_dt:
        return []

    open_ts = open_dt.timestamp()

    return [
        c for c in candles
        if c["ts"] < open_ts
    ]


def calculate_model(candles, market_open, target):
    """
    Calcula una lectura usando únicamente información anterior
    al comienzo de la vela. Esta parte es la base del modelo.
    """

    if len(candles) < 16:
        return {
            "direction": "SUBE",
            "probability": 0.55,
            "strength": 1,
            "momentum": 0.0,
        }

    closes = [c["close"] for c in candles]

    last = closes[-1]

    def ret(minutes):
        if len(closes) <= minutes:
            return 0.0

        previous = closes[-1 - minutes]

        if previous == 0:
            return 0.0

        return (last / previous) - 1.0

    r1 = ret(1)
    r3 = ret(3)
    r5 = ret(5)
    r10 = ret(10)
    r15 = ret(15)

    momentum = (
        r1 * 0.30
        + r3 * 0.25
        + r5 * 0.20
        + r10 * 0.15
        + r15 * 0.10
    )

    # Si conocemos el objetivo, incorporamos la distancia previa.
    target_bias = 0.0

    if target and last > 0:
        distance = (last - target) / last

        # Pequeña influencia, sin dominar al momentum.
        target_bias = max(-0.004, min(0.004, distance * 0.20))

    score = momentum + target_bias

    # Escala conservadora para producir probabilidades 55%-84%.
    scaled = abs(score) * 650

    probability = 0.55 + min(0.29, scaled)

    if score >= 0:
        direction = "SUBE"
    else:
        direction = "BAJA"

    if probability >= 0.77:
        strength = 3
    elif probability >= 0.64:
        strength = 2
    else:
        strength = 1

    return {
        "direction": direction,
        "probability": probability,
        "strength": strength,
        "momentum": momentum,
        "last_before_open": last,
    }


def calculate_max_entry(probability):
    if probability is None:
        return None

    return probability / (1.0 + MIN_EXPECTED_RETURN)


def money(value):
    if value is None:
        return "—"

    return f"${value:,.2f}"


def pct(value, decimals=0):
    if value is None:
        return "—"

    return f"{value * 100:.{decimals}f}%"


def format_ny(dt):
    if not dt:
        return "—"

    return dt.astimezone(NY).strftime("%-I:%M %p")


def countdown(close_dt):
    if not close_dt:
        return "—"

    now = datetime.now(timezone.utc)
    seconds = max(0, int((close_dt - now).total_seconds()))

    minutes = seconds // 60
    secs = seconds % 60

    return f"{minutes:02d}:{secs:02d}"


def projected_close(current_price, target, direction, close_dt):
    if current_price is None or target is None or not close_dt:
        return None

    now = datetime.now(timezone.utc)

    remaining = max(0, (close_dt - now).total_seconds())

    # Proyección moderada. No intenta predecir movimientos extremos.
    max_move = 0.015

    if direction == "SUBE":
        projected = current_price * (1 + max_move * min(1, remaining / 900))
    else:
        projected = current_price * (1 - max_move * min(1, remaining / 900))

    return projected


def live_direction(probability):
    if probability is None:
        return "—"

    return "SUBE" if probability >= 0.50 else "BAJA"


# ============================================================
# DATOS ACTUALES
# ============================================================

market = get_current_market()

btc_price = get_btc_price()

kalshi_prob = get_kalshi_probability(market)

target = get_market_target(market)

if market:
    open_dt = parse_dt(market.get("open_time"))
    close_dt = parse_dt(market.get("close_time"))
else:
    open_dt = None
    close_dt = None


# ============================================================
# MODELO
# ============================================================

historical = get_historical_before_open(open_dt)

model = calculate_model(
    historical,
    open_dt,
    target,
)

direction = model["direction"]
probability = model["probability"]
strength = model["strength"]

max_entry = calculate_max_entry(probability)

live_dir = live_direction(kalshi_prob)


# ============================================================
# CAMBIO DE BTC
# ============================================================

btc_change = None

if historical and btc_price:
    reference = historical[-1]["close"]

    if reference:
        btc_change = (btc_price / reference) - 1


# ============================================================
# GUÍA DE CIERRE
# ============================================================

projection = projected_close(
    btc_price,
    target,
    direction,
    close_dt,
)

if btc_price and target:
    distance = (btc_price - target) / target
else:
    distance = None

if close_dt:
    now = datetime.now(timezone.utc)
    seconds_left = max(1, (close_dt - now).total_seconds())
else:
    seconds_left = 900

if btc_price and projection and seconds_left > 0:
    required_rate = (projection - btc_price) / seconds_left
else:
    required_rate = 0

required_rate_display = required_rate * btc_price if btc_price else 0


# ============================================================
# RADAR
# ============================================================

radar_text = "La dirección principal permanece fija durante esta vela."

if kalshi_prob is not None:
    live_gap = abs(kalshi_prob - probability)

    if live_gap >= 0.15:
        radar_text = (
            "⚠️ El mercado de Kalshi se está separando bastante "
            "de la probabilidad del modelo."
        )
    elif live_gap >= 0.08:
        radar_text = (
            "👀 Hay una diferencia relevante entre el modelo "
            "y la lectura en vivo de Kalshi."
        )
    else:
        radar_text = (
            "✅ Kalshi permanece relativamente alineado "
            "con la lectura del modelo."
        )


# ============================================================
# CONFIRMACIÓN
# ============================================================

if strength >= 3:
    confirmation = 3
elif strength == 2:
    confirmation = 2
else:
    confirmation = 1


# ============================================================
# HEADER
# ============================================================

now_ny = datetime.now(NY)

st.markdown(
    f"""
    <div class="topbar">
        <div class="brand">
            <div class="btc-icon">₿</div>
            <div>
                <div class="title">BTC • 15 MIN</div>
                <div class="subtitle">Predictor • Kalshi</div>
            </div>
        </div>

        <div class="live">
            <span class="live-dot"></span> EN VIVO<br>
            {now_ny.strftime("%-I:%M:%S %p")}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LECTURA ACTUAL
# ============================================================

signal_class = "signal-up" if direction == "SUBE" else "signal-down"
signal_icon = "▲" if direction == "SUBE" else "▼"
signal_text = direction

change_html = ""

if btc_change is not None:
    change_class = "change-up" if btc_change >= 0 else "change-down"
    change_html = (
        f'<div class="{change_class}">'
        f'{btc_change * 100:+.2f}%'
        f'</div>'
    )

bars = ""

for i in range(3):
    active = "active" if i < confirmation else ""
    bars += f'<div class="bar {active}"></div>'

st.markdown(
    f"""
    <div class="card main-card">
        <div class="section-title">LECTURA ACTUAL</div>

        <div class="signal-row">
            <div>
                <div class="signal {signal_class}">
                    {signal_icon} {signal_text}
                </div>

                <div class="locked">
                    🔒 Dirección fija
                </div>

                <div class="price">
                    {money(btc_price)}
                </div>

                {change_html}
            </div>

            <div class="prob">
                <div class="prob-number">
                    {pct(probability)}
                </div>
                <div class="prob-label">
                    probabilidad estimada
                </div>
            </div>
        </div>

        <div class="confirm-title">
            Confirmación progresiva: {confirmation}/3
        </div>

        <div class="bars">
            {bars}
        </div>

        <div class="notice">
            <div class="notice-title">
                🎯 {direction} activa
            </div>

            <div class="notice-text">
                La dirección permanece fija durante esta vela.
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# OBJETIVO + CIERRE
# ============================================================

st.markdown(
    f"""
    <div class="grid">

        <div class="small-card">
            <div class="small-title">
                🎯 OBJETIVO KALSHI
            </div>

            <div class="small-value">
                {money(target)}
            </div>

            <div class="small-sub">
                Distancia: {pct(distance, 3)}
            </div>
        </div>

        <div class="small-card">
            <div class="small-title">
                ⏱️ CIERRE
            </div>

            <div class="small-value">
                {countdown(close_dt)}
            </div>

            <div class="small-sub">
                Cierre: {format_ny(close_dt)}
            </div>
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# GUÍA PARA EL CIERRE
# ============================================================

guide_class = "guide-up" if direction == "SUBE" else "guide-down"

st.markdown(
    f"""
    <div class="card guide">
        <div class="section-title">
            GUÍA PARA EL CIERRE
        </div>

        <div class="guide-title {guide_class}">
            PROBABLE CIERRE {direction}
            <span style="float:right">{pct(probability)}</span>
        </div>

        <div class="guide-text">
            El cálculo usa el movimiento previo y la estructura
            de la vela. La lectura puede cambiar para la próxima vela.
        </div>

        <div class="metrics">

            <div class="metric">
                <div class="metric-label">
                    CIERRE PROYECTADO
                </div>

                <div class="metric-value">
                    {money(projection)}
                </div>
            </div>

            <div class="metric">
                <div class="metric-label">
                    RITMO ACTUAL
                </div>

                <div class="metric-value">
                    {required_rate_display:+.2f} $/s
                </div>
            </div>

            <div class="metric">
                <div class="metric-label">
                    RITMO NECESARIO
                </div>

                <div class="metric-value">
                    {required_rate_display:+.2f} $/s
                </div>
            </div>

        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# KALSHI EN VIVO
# ============================================================

if kalshi_prob is not None:
    live_yes = kalshi_prob
    live_no = 1 - kalshi_prob
else:
    live_yes = 0.50
    live_no = 0.50

st.markdown(
    f"""
    <div class="card">

        <div class="kalshi-title">
            📊 KALSHI EN VIVO
        </div>

        <div class="kalshi-row">
            <span class="green">
                🟢 SUBE {pct(live_yes)}
            </span>

            <span class="red">
                🔴 BAJA {pct(live_no)}
            </span>
        </div>

        <div class="live-bar">
            <div class="live-up" style="width:{live_yes * 100}%"></div>
            <div class="live-down" style="width:{live_no * 100}%"></div>
        </div>

        <div class="small-sub" style="margin-top:10px;">
            Lectura en vivo de Kalshi. Esta lectura es independiente
            de la dirección principal fijada por el modelo.
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ENTRADA
# ============================================================

st.markdown(
    f"""
    <div class="card entry">

        <div class="entry-title">
            💰 GUÍA DE ENTRADA
        </div>

        <div class="entry-number">
            Entrada máxima sugerida: {pct(max_entry)}
        </div>

        <div class="entry-sub">
            Basada en una exigencia aproximada de
            {MIN_EXPECTED_RETURN * 100:.0f}% de retorno bruto.
        </div>

        <div class="entry-sub">
            Posición sugerida: {SUGGESTED_POSITION}% —
            solo como referencia, sin compra automática.
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# RADAR
# ============================================================

st.markdown(
    f"""
    <div class="card radar">

        <div class="radar-title">
            🚨 RADAR
        </div>

        <div class="radar-text">
            {radar_text}
        </div>

        <div class="radar-text">
            Modelo: <b>{direction}</b> ·
            Kalshi en vivo: <b>{live_dir}</b> ·
            Fuerza: <b>{strength}/3</b>
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PRÓXIMA VELA
# ============================================================

if close_dt:
    remaining = (close_dt - datetime.now(timezone.utc)).total_seconds()
else:
    remaining = 9999

if remaining <= PREVIEW_SECONDS:

    next_market = get_next_market()

    if next_market:
        next_open = parse_dt(next_market.get("open_time"))
        next_target = get_market_target(next_market)

        preview_candles = get_historical_before_open(next_open)

        preview_model = calculate_model(
            preview_candles,
            next_open,
            next_target,
        )

        preview_direction = preview_model["direction"]
        preview_probability = preview_model["probability"]

        st.markdown(
            f"""
            <div class="card preview">

                <div class="preview-title">
                    🔮 PRÓXIMA VELA
                </div>

                <div class="preview-value">
                    {preview_direction}
                    · {pct(preview_probability)}
                </div>

                <div class="small-sub">
                    Vista previa. No modifica la dirección de la
                    vela actual.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        Señales solamente · Sin compras automáticas ·
        BTC 15 MIN · Hora de Nueva York
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ACTUALIZACIÓN
# ============================================================

time.sleep(REFRESH_SECONDS)
st.rerun()
