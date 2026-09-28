import math
import time
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
    initial_sidebar_state="collapsed",
)

NY = ZoneInfo("America/New_York")

SERIES = "KXBTC15M"

REFRESH_SECONDS = 10
PREVIEW_SECONDS = 180
POSITION_PERCENT = 25
MIN_EXPECTED_RETURN = 0.10

KRAKEN_URL = "https://api.kraken.com/0/public/OHLC"

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
        radial-gradient(circle at top, #18212b 0%, #0b0f14 45%, #070a0e 100%);
    color: #f5f7fa;
}

.block-container {
    max-width: 720px;
    padding-top: 1rem;
    padding-bottom: 2rem;
    padding-left: 0.75rem;
    padding-right: 0.75rem;
}

.header {
    background: linear-gradient(135deg, #151d27, #0c1117);
    border: 1px solid #283442;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,.30);
}

.header-title {
    font-size: 25px;
    font-weight: 800;
    letter-spacing: .5px;
}

.header-sub {
    color: #9ba8b7;
    font-size: 13px;
    margin-top: 3px;
}

.live {
    display: inline-block;
    margin-top: 12px;
    padding: 5px 9px;
    border-radius: 999px;
    background: rgba(34,197,94,.12);
    border: 1px solid rgba(34,197,94,.35);
    color: #58e58a;
    font-size: 11px;
    font-weight: 700;
}

.card {
    background: rgba(16,22,29,.96);
    border: 1px solid #273340;
    border-radius: 16px;
    padding: 16px;
    margin: 10px 0;
    box-shadow: 0 8px 25px rgba(0,0,0,.20);
}

.section-title {
    color: #8d9aaa;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
    margin-bottom: 10px;
}

.signal {
    text-align: center;
    font-size: 34px;
    font-weight: 900;
    padding: 13px;
    border-radius: 14px;
    margin: 8px 0 12px;
}

.signal-green {
    background: rgba(34,197,94,.10);
    border: 1px solid rgba(34,197,94,.40);
    color: #4ade80;
}

.signal-red {
    background: rgba(239,68,68,.10);
    border: 1px solid rgba(239,68,68,.40);
    color: #ff6868;
}

.prob {
    text-align: center;
    font-size: 37px;
    font-weight: 900;
    margin: 2px 0;
}

.center {
    text-align: center;
}

.muted {
    color: #8f9baa;
    font-size: 12px;
}

.big {
    font-size: 22px;
    font-weight: 800;
}

.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 9px;
}

.metric {
    background: #111821;
    border: 1px solid #26313d;
    border-radius: 12px;
    padding: 11px;
}

.metric-label {
    color: #7f8b99;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .7px;
}

.metric-value {
    font-size: 17px;
    font-weight: 800;
    margin-top: 4px;
}

.green {
    color: #4ade80;
}

.red {
    color: #ff6868;
}

.yellow {
    color: #facc15;
}

.blue {
    color: #60a5fa;
}

.alert {
    border: 1px solid rgba(250,204,21,.45);
    background: rgba(250,204,21,.08);
    color: #fde68a;
    border-radius: 12px;
    padding: 12px;
    font-weight: 800;
    text-align: center;
    margin-top: 8px;
}

.good {
    border: 1px solid rgba(34,197,94,.35);
    background: rgba(34,197,94,.07);
    color: #86efac;
    border-radius: 12px;
    padding: 11px;
    text-align: center;
    font-weight: 700;
}

.wait {
    border: 1px solid rgba(250,204,21,.35);
    background: rgba(250,204,21,.07);
    color: #fde68a;
    border-radius: 12px;
    padding: 11px;
    text-align: center;
    font-weight: 700;
}

.footer {
    text-align: center;
    color: #657180;
    font-size: 10px;
    padding: 12px;
}

@media (max-width: 500px) {

    .block-container {
        padding-left: .55rem;
        padding-right: .55rem;
    }

    .header-title {
        font-size: 22px;
    }

    .signal {
        font-size: 29px;
    }

    .prob {
        font-size: 32px;
    }

    .big {
        font-size: 19px;
    }

    .metric-value {
        font-size: 15px;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FUNCIONES
# ============================================================

def now_ny():
    return datetime.now(timezone.utc).astimezone(NY)


def parse_time(value):
    if value is None:
        return None

    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(
                float(value), tz=timezone.utc
            )

        text = str(value).replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def money(value):
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "—"


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "—"


def get_json(url, params=None, timeout=8):
    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
        )

        response.raise_for_status()

        return response.json()

    except Exception:
        return None


# ============================================================
# BTC KRAKEN
# ============================================================

def get_btc_price():
    data = get_json(
        KRAKEN_URL,
        params={
            "pair": "XBTUSD",
            "interval": 1,
        },
    )

    if not data:
        return None

    try:
        result = data["result"]

        pair_key = next(
            key for key in result
            if key != "last"
        )

        candles = result[pair_key]

        if not candles:
            return None

        last = candles[-1]

        return float(last[4])

    except Exception:
        return None


def get_btc_history():
    data = get_json(
        KRAKEN_URL,
        params={
            "pair": "XBTUSD",
            "interval": 1,
        },
        timeout=10,
    )

    if not data:
        return []

    try:
        result = data["result"]

        pair_key = next(
            key for key in result
            if key != "last"
        )

        candles = result[pair_key]

        output = []

        for candle in candles:

            output.append(
                {
                    "time": datetime.fromtimestamp(
                        float(candle[0]),
                        tz=timezone.utc,
                    ),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                }
            )

        return output

    except Exception:
        return []


# ============================================================
# KALSHI
# ============================================================

def get_kalshi_markets():

    for host in KALSHI_HOSTS:

        url = f"{host}/markets"

        data = get_json(
            url,
            params={
                "series_ticker": SERIES,
                "status": "open",
                "limit": 100,
            },
            timeout=10,
        )

        if not data:
            continue

        markets = data.get("markets", [])

        if markets:
            return markets

    return []


def get_active_market():

    markets = get_kalshi_markets()

    if not markets:
        return None

    current = datetime.now(timezone.utc)

    valid = []

    for market in markets:

        open_time = parse_time(
            market.get("open_time")
        )

        close_time = parse_time(
            market.get("close_time")
        )

        if not open_time or not close_time:
            continue

        if open_time <= current < close_time:
            valid.append(market)

    if not valid:
        return None

    valid.sort(
        key=lambda x: parse_time(
            x.get("close_time")
        ) or current
    )

    return valid[0]


# ============================================================
# PRECIO / TARGET DE KALSHI
# ============================================================

def kalshi_probability(market):

    yes_bid = market.get("yes_bid_dollars")
    yes_ask = market.get("yes_ask_dollars")
    last = market.get("last_price_dollars")

    values = []

    try:
        if yes_bid is not None:
            values.append(float(yes_bid))

        if yes_ask is not None:
            values.append(float(yes_ask))

        if len(values) >= 2:
            return max(
                0.01,
                min(
                    0.99,
                    sum(values[:2]) / 2
                ),
            )

        if last is not None:
            return max(
                0.01,
                min(
                    0.99,
                    float(last)
                ),
            )

    except Exception:
        pass

    return 0.50


def get_target(market):

    for field in [
        "floor_strike",
        "custom_strike",
        "cap_strike",
        "strike",
    ]:

        value = market.get(field)

        if value is not None:

            try:
                return float(value)

            except Exception:
                pass

    return None


# ============================================================
# MODELO
# ============================================================

def percentage_change(old, new):

    if old == 0:
        return 0

    return (new - old) / old


def calculate_model(history, open_time):

    if not history:
        return 0.50, "MEDIA"

    before_open = [
        x for x in history
        if x["time"] < open_time
    ]

    if len(before_open) < 20:
        return 0.50, "MEDIA"

    closes = [
        x["close"]
        for x in before_open
    ]

    current = closes[-1]

    def change(minutes):

        if len(closes) <= minutes:
            return 0

        old = closes[-1 - minutes]

        return percentage_change(
            old,
            current,
        )

    c1 = change(1)
    c3 = change(3)
    c5 = change(5)
    c10 = change(10)
    c15 = change(15)

    momentum = (
        c1 * 0.10
        + c3 * 0.20
        + c5 * 0.25
        + c10 * 0.25
        + c15 * 0.20
    )

    recent = closes[-30:]

    if len(recent) > 2:

        returns = []

        for i in range(1, len(recent)):
            returns.append(
                percentage_change(
                    recent[i - 1],
                    recent[i],
                )
            )

        avg = sum(returns) / len(returns)

        variance = sum(
            (x - avg) ** 2
            for x in returns
        ) / len(returns)

        volatility = math.sqrt(variance)

    else:
        volatility = 0

    score = momentum * 100000

    volatility_factor = min(
        1.0,
        max(
            0.35,
            1.0 - volatility * 1200,
        ),
    )

    score *= volatility_factor

    probability = 0.50 + (
        max(
            -0.34,
            min(
                0.34,
                score,
            ),
        )
    )

    probability = max(
        0.55,
        min(
            0.84,
            probability,
        ),
    )

    distance = abs(probability - 0.50)

    if distance >= 0.22:
        strength = "FUERTE"

    elif distance >= 0.13:
        strength = "MEDIA"

    else:
        strength = "BAJA"

    return probability, strength


# ============================================================
# SEÑAL FIJA
# ============================================================

@st.cache_data(
    show_spinner=False,
    ttl=900,
)
def locked_signal(
    ticker,
    open_time_iso,
):

    open_time = parse_time(open_time_iso)

    history = get_btc_history()

    probability, strength = calculate_model(
        history,
        open_time,
    )

    direction = (
        "SUBE"
        if probability >= 0.50
        else "BAJA"
    )

    return {
        "direction": direction,
        "probability": probability,
        "strength": strength,
    }


# ============================================================
# PRÓXIMA VELA
# ============================================================

def preview_signal(
    history,
    next_open,
):

    probability, strength = calculate_model(
        history,
        next_open,
    )

    direction = (
        "SUBE"
        if probability >= 0.50
        else "BAJA"
    )

    return direction, probability, strength


# ============================================================
# ENTRADA
# ============================================================

def calculate_max_entry(probability):

    return probability / (
        1 + MIN_EXPECTED_RETURN
    )


# ============================================================
# PROYECCIÓN
# ============================================================

def projected_close(
    btc_price,
    history,
    seconds_left,
):

    if not history or seconds_left <= 0:
        return btc_price

    recent = [
        x["close"]
        for x in history[-6:]
    ]

    if len(recent) < 2:
        return btc_price

    first = recent[0]
    last = recent[-1]

    elapsed_minutes = max(
        1,
        len(recent) - 1,
    )

    velocity = (
        last - first
    ) / elapsed_minutes

    remaining_minutes = (
        seconds_left / 60
    )

    projection = (
        btc_price
        + velocity * remaining_minutes
    )

    return projection


# ============================================================
# HEADER
# ============================================================

current_time = now_ny()

st.markdown(
    f"""
<div class="header">

    <div class="header-title">
        ₿ BTC • 15 MIN
    </div>

    <div class="header-sub">
        Predictor • Kalshi
    </div>

    <div class="live">
        ● EN VIVO
    </div>

    <div class="muted" style="margin-top:8px;">
        {current_time.strftime("%m/%d/%Y • %I:%M:%S %p")} New York
    </div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# OBTENER MERCADO
# ============================================================

market = get_active_market()

btc_price = get_btc_price()

history = get_btc_history()


if not market:

    st.markdown(
        """
<div class="card">

    <div class="section-title">
        ESTADO
    </div>

    <div class="center">
        <div class="big">
            Esperando mercado BTC 15M
        </div>

        <div class="muted" style="margin-top:7px;">
            Kalshi todavía no devolvió una vela activa.
        </div>
    </div>

</div>
""",
        unsafe_allow_html=True,
    )

    time.sleep(REFRESH_SECONDS)
    st.rerun()


# ============================================================
# DATOS DEL MERCADO
# ============================================================

ticker = market.get(
    "ticker",
    "KXBTC15M",
)

open_time = parse_time(
    market.get("open_time")
)

close_time = parse_time(
    market.get("close_time")
)

if not open_time or not close_time:

    st.error(
        "No se pudo leer el horario del mercado."
    )

    time.sleep(REFRESH_SECONDS)
    st.rerun()


# ============================================================
# SEÑAL BLOQUEADA
# ============================================================

signal = locked_signal(
    ticker,
    open_time.isoformat(),
)

direction = signal["direction"]

model_probability = signal["probability"]

strength = signal["strength"]


# ============================================================
# TIEMPO
# ============================================================

now_utc = datetime.now(timezone.utc)

seconds_left = max(
    0,
    int(
        (
            close_time - now_utc
        ).total_seconds()
    ),
)

minutes_left = seconds_left // 60

seconds_only = seconds_left % 60


# ============================================================
# KALSHI
# ============================================================

kalshi_prob = kalshi_probability(
    market
)

kalshi_up = kalshi_prob

kalshi_down = 1 - kalshi_prob

target = get_target(market)


# ============================================================
# ENTRADA
# ============================================================

max_entry = calculate_max_entry(
    model_probability
)

current_entry = kalshi_prob


entry_good = (
    current_entry <= max_entry
)


# ============================================================
# PROYECCIÓN
# ============================================================

projection = projected_close(
    btc_price,
    history,
    seconds_left,
)

if btc_price is not None and target is not None:

    distance_target = (
        target - btc_price
    )

else:

    distance_target = None


# ============================================================
# LECTURA PRINCIPAL
# ============================================================

signal_class = (
    "signal-green"
    if direction == "SUBE"
    else "signal-red"
)

signal_icon = (
    "🟢"
    if direction == "SUBE"
    else "🔴"
)

direction_class = (
    "green"
    if direction == "SUBE"
    else "red"
)


st.markdown(
    f"""
<div class="card">

    <div class="section-title">
        LECTURA ACTUAL
    </div>

    <div class="signal {signal_class}">
        {signal_icon} {direction}
    </div>

    <div class="prob">
        {model_probability * 100:.1f}%
    </div>

    <div class="center muted">
        Probabilidad del modelo
    </div>

    <div class="grid" style="margin-top:12px;">

        <div class="metric">
            <div class="metric-label">
                Fuerza
            </div>

            <div class="metric-value {direction_class}">
                {strength}
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">
                Vela
            </div>

            <div class="metric-value">
                {ticker}
            </div>
        </div>

    </div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# BTC
# ============================================================

st.markdown(
    f"""
<div class="card">

    <div class="section-title">
        BTC EN VIVO
    </div>

    <div class="center">

        <div class="big">
            {money(btc_price)}
        </div>

        <div class="muted">
            Precio actual de Bitcoin
        </div>

    </div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# TARGET + COUNTDOWN
# ============================================================

target_text = (
    money(target)
    if target is not None
    else "—"
)

distance_text = (
    money(distance_target)
    if distance_target is not None
    else "—"
)


st.markdown(
    f"""
<div class="card">

    <div class="section-title">
        OBJETIVO Y CIERRE
    </div>

    <div class="grid">

        <div class="metric">
            <div class="metric-label">
                Target Kalshi
            </div>

            <div class="metric-value blue">
                {target_text}
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">
                Tiempo restante
            </div>

            <div class="metric-value yellow">
                {minutes_left:02d}:{seconds_only:02d}
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">
                Distancia al target
            </div>

            <div class="metric-value">
                {distance_text}
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">
                Cierre proyectado
            </div>

            <div class="metric-value">
                {money(projection)}
            </div>
        </div>

    </div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# KALSHI LIVE
# ============================================================

kalshi_side = (
    "SUBE"
    if kalshi_up >= 0.50
    else "BAJA"
)

kalshi_side_icon = (
    "🟢"
    if kalshi_side == "SUBE"
    else "🔴"
)

kalshi_side_class = (
    "green"
    if kalshi_side == "SUBE"
    else "red"
)


st.markdown(
    f"""
<div class="card">

    <div class="section-title">
        KALSHI EN VIVO
    </div>

    <div class="center">

        <div class="big {kalshi_side_class}">
            {kalshi_side_icon} {kalshi_side}
        </div>

    </div>

    <div class="grid" style="margin-top:12px;">

        <div class="metric">
            <div class="metric-label">
                SUBE
            </div>

            <div class="metric-value green">
                {kalshi_up * 100:.1f}%
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">
                BAJA
            </div>

            <div class="metric-value red">
                {kalshi_down * 100:.1f}%
            </div>
        </div>

    </div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# RADAR DE GIRO
# ============================================================

turn_detected = (
    kalshi_side != direction
    and abs(kalshi_prob - 0.50) >= 0.07
)

if turn_detected:

    st.markdown(
        f"""
<div class="alert">
    🚨 ALERTA DE GIRO<br>
    {direction} → {kalshi_side}
</div>
""",
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
<div class="good">
    📡 RADAR<br>
    Sin giro significativo
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# ENTRADA
# ============================================================

entry_status = (
    "FAVORABLE"
    if entry_good
    else "EN LÍMITE"
)

entry_class = (
    "good"
    if entry_good
    else "wait"
)


st.markdown(
    f"""
<div class="card">

    <div class="section-title">
        ENTRADA
    </div>

    <div class="grid">

        <div class="metric">
            <div class="metric-label">
                Modelo
            </div>

            <div class="metric-value">
                {model_probability * 100:.1f}%
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">
                Entrada actual
            </div>

            <div class="metric-value">
                {current_entry * 100:.1f}%
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">
                Máximo sugerido
            </div>

            <div class="metric-value yellow">
                {max_entry * 100:.1f}%
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">
                Posición
            </div>

            <div class="metric-value blue">
                {POSITION_PERCENT}%
            </div>
        </div>

    </div>

    <div class="{entry_class}" style="margin-top:12px;">
        {entry_status}
    </div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# PRÓXIMA VELA
# ============================================================

if seconds_left <= PREVIEW_SECONDS:

    next_open = close_time

    next_direction, next_probability, next_strength = (
        preview_signal(
            history,
            next_open,
        )
    )

    next_icon = (
        "🟢"
        if next_direction == "SUBE"
        else "🔴"
    )

    st.markdown(
        f"""
<div class="card">

    <div class="section-title">
        PRÓXIMA VELA
    </div>

    <div class="center">

        <div class="big">
            {next_icon} {next_direction}
        </div>

        <div style="font-size:25px;font-weight:900;margin-top:4px;">
            {next_probability * 100:.1f}%
        </div>

        <div class="muted">
            Fuerza: {next_strength}
        </div>

        <div class="muted" style="margin-top:8px;">
            Vista preliminar — todavía no reemplaza la señal actual.
        </div>

    </div>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# INFORMACIÓN
# ============================================================

st.markdown(
    """
<div class="footer">
    Señal principal bloqueada por vela de 15 minutos.<br>
    Los datos de Kalshi se actualizan en vivo.<br>
    Este bot genera señales y no ejecuta órdenes automáticamente.
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# ACTUALIZACIÓN
# ============================================================

time.sleep(REFRESH_SECONDS)

st.rerun()
