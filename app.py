import math
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from textwrap import dedent

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
# HTML
# ============================================================

def render_html(content):
    """
    Renderiza HTML correctamente en Streamlit.
    dedent elimina espacios innecesarios de las líneas.
    """
    st.markdown(
        dedent(content),
        unsafe_allow_html=True,
    )


# ============================================================
# ESTILO
# ============================================================

render_html(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at top,
                #18222d 0%,
                #0c1117 45%,
                #070a0e 100%
            );
        color: #f5f7fa;
    }

    .block-container {
        max-width: 720px;
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: .65rem;
        padding-right: .65rem;
    }

    .header {
        background: linear-gradient(
            135deg,
            #17212c,
            #0d131a
        );
        border: 1px solid #293746;
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,.30);
    }

    .header-title {
        font-size: 24px;
        font-weight: 900;
        letter-spacing: .4px;
    }

    .header-sub {
        color: #9aa7b5;
        font-size: 13px;
        margin-top: 3px;
    }

    .live {
        display: inline-block;
        margin-top: 11px;
        padding: 5px 9px;
        border-radius: 999px;
        background: rgba(34,197,94,.10);
        border: 1px solid rgba(34,197,94,.35);
        color: #55e98a;
        font-size: 10px;
        font-weight: 800;
    }

    .card {
        background: rgba(15,21,28,.97);
        border: 1px solid #283542;
        border-radius: 16px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 8px 25px rgba(0,0,0,.22);
    }

    .section-title {
        color: #8b99a8;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 1px;
        margin-bottom: 9px;
    }

    .signal {
        text-align: center;
        font-size: 31px;
        font-weight: 900;
        padding: 13px;
        border-radius: 14px;
        margin: 7px 0 12px;
    }

    .signal-green {
        background: rgba(34,197,94,.09);
        border: 1px solid rgba(34,197,94,.38);
        color: #4ade80;
    }

    .signal-red {
        background: rgba(239,68,68,.09);
        border: 1px solid rgba(239,68,68,.38);
        color: #ff6868;
    }

    .prob {
        text-align: center;
        font-size: 36px;
        font-weight: 900;
        margin: 2px 0;
    }

    .center {
        text-align: center;
    }

    .muted {
        color: #8996a4;
        font-size: 11px;
    }

    .big {
        font-size: 21px;
        font-weight: 900;
    }

    .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
    }

    .metric {
        background: #111820;
        border: 1px solid #26323e;
        border-radius: 12px;
        padding: 10px;
    }

    .metric-label {
        color: #788694;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: .65px;
    }

    .metric-value {
        font-size: 16px;
        font-weight: 850;
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
        margin: 10px 0;
    }

    .good {
        border: 1px solid rgba(34,197,94,.35);
        background: rgba(34,197,94,.07);
        color: #86efac;
        border-radius: 12px;
        padding: 11px;
        text-align: center;
        font-weight: 800;
        margin-top: 10px;
    }

    .wait {
        border: 1px solid rgba(250,204,21,.35);
        background: rgba(250,204,21,.07);
        color: #fde68a;
        border-radius: 12px;
        padding: 11px;
        text-align: center;
        font-weight: 800;
        margin-top: 10px;
    }

    .footer {
        text-align: center;
        color: #64717f;
        font-size: 9px;
        padding: 12px;
        line-height: 1.6;
    }

    @media (max-width: 500px) {

        .block-container {
            padding-left: .5rem;
            padding-right: .5rem;
        }

        .header-title {
            font-size: 21px;
        }

        .signal {
            font-size: 28px;
        }

        .prob {
            font-size: 32px;
        }

        .big {
            font-size: 19px;
        }

        .metric-value {
            font-size: 14px;
        }
    }

    </style>
    """
)


# ============================================================
# UTILIDADES
# ============================================================

def now_ny():
    return datetime.now(timezone.utc).astimezone(NY)


def parse_time(value):
    if value is None:
        return None

    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(
                float(value),
                tz=timezone.utc,
            )

        text = str(value).replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def money(value):
    if value is None:
        return "—"

    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "—"


def safe_get(url, params=None, timeout=8):

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
# BTC
# ============================================================

def get_btc_history():

    data = safe_get(
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

        result = data.get("result", {})

        pair_key = next(
            key
            for key in result
            if key != "last"
        )

        candles = result[pair_key]

        history = []

        for candle in candles:

            history.append(
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

        return history

    except Exception:
        return []


def get_btc_price(history):

    if not history:
        return None

    try:
        return history[-1]["close"]
    except Exception:
        return None


# ============================================================
# KALSHI
# ============================================================

def get_kalshi_markets():

    for host in KALSHI_HOSTS:

        data = safe_get(
            f"{host}/markets",
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

    active = []

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
            active.append(market)

    if not active:
        return None

    active.sort(
        key=lambda market:
        parse_time(
            market.get("close_time")
        ) or current
    )

    return active[0]


def get_kalshi_probability(market):

    if not market:
        return 0.50

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

            bid_value = float(bid)
            ask_value = float(ask)

            return max(
                0.01,
                min(
                    0.99,
                    (bid_value + ask_value) / 2,
                ),
            )

        if last is not None:

            return max(
                0.01,
                min(
                    0.99,
                    float(last),
                ),
            )

    except Exception:
        pass

    return 0.50


def get_target(market):

    if not market:
        return None

    fields = [
        "floor_strike",
        "custom_strike",
        "cap_strike",
        "strike",
    ]

    for field in fields:

        value = market.get(field)

        if value is None:
            continue

        try:
            return float(value)
        except Exception:
            continue

    return None


# ============================================================
# CAMBIOS DE BTC
# ============================================================

def price_change(closes, minutes):

    if len(closes) <= minutes:
        return 0.0

    old = closes[-1 - minutes]
    new = closes[-1]

    if old == 0:
        return 0.0

    return (new - old) / old


# ============================================================
# MODELO
# ============================================================

def calculate_model(history, market_open):

    if not history or not market_open:
        return 0.50, "BAJA"

    before_open = [
        candle
        for candle in history
        if candle["time"] < market_open
    ]

    if len(before_open) < 20:
        return 0.50, "BAJA"

    closes = [
        candle["close"]
        for candle in before_open
    ]

    c1 = price_change(closes, 1)
    c3 = price_change(closes, 3)
    c5 = price_change(closes, 5)
    c10 = price_change(closes, 10)
    c15 = price_change(closes, 15)

    momentum = (
        c1 * 0.10
        + c3 * 0.20
        + c5 * 0.25
        + c10 * 0.25
        + c15 * 0.20
    )

    recent = closes[-30:]

    returns = []

    for i in range(1, len(recent)):

        old = recent[i - 1]
        new = recent[i]

        if old != 0:
            returns.append(
                (new - old) / old
            )

    if returns:

        average = sum(returns) / len(returns)

        variance = sum(
            (r - average) ** 2
            for r in returns
        ) / len(returns)

        volatility = math.sqrt(
            variance
        )

    else:
        volatility = 0.0

    score = momentum * 100000

    volatility_factor = max(
        0.35,
        min(
            1.0,
            1.0 - volatility * 1200,
        ),
    )

    score *= volatility_factor

    score = max(
        -0.34,
        min(
            0.34,
            score,
        ),
    )

    probability = 0.50 + score

    probability = max(
        0.16,
        min(
            0.84,
            probability,
        ),
    )

    distance = abs(
        probability - 0.50
    )

    if distance >= 0.22:
        strength = "FUERTE"

    elif distance >= 0.12:
        strength = "MEDIA"

    else:
        strength = "BAJA"

    return probability, strength


# ============================================================
# SEÑAL FIJA DE LA VELA
# ============================================================

@st.cache_data(
    show_spinner=False,
    ttl=900,
)
def locked_signal(
    ticker,
    open_time_iso,
):

    open_time = parse_time(
        open_time_iso
    )

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

def calculate_preview(
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

    return (
        direction,
        probability,
        strength,
    )


# ============================================================
# ENTRADA MÁXIMA
# ============================================================

def max_entry_price(probability):

    return probability / (
        1.0 + MIN_EXPECTED_RETURN
    )


# ============================================================
# PROYECCIÓN
# ============================================================

def projected_close(
    btc_price,
    history,
    seconds_left,
):

    if (
        btc_price is None
        or not history
        or seconds_left <= 0
    ):
        return btc_price

    recent = history[-6:]

    if len(recent) < 2:
        return btc_price

    first = recent[0]["close"]
    last = recent[-1]["close"]

    minutes = len(recent) - 1

    if minutes <= 0:
        return btc_price

    velocity = (
        last - first
    ) / minutes

    remaining_minutes = (
        seconds_left / 60
    )

    return (
        btc_price
        + velocity * remaining_minutes
    )


# ============================================================
# HEADER
# ============================================================

current = now_ny()

render_html(
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
            {current.strftime("%m/%d/%Y • %I:%M:%S %p")} • New York
        </div>

    </div>
    """
)


# ============================================================
# OBTENER DATOS
# ============================================================

history = get_btc_history()

btc_price = get_btc_price(
    history
)

market = get_active_market()


# ============================================================
# SI NO HAY MERCADO
# ============================================================

if not market:

    render_html(
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
                    Buscando la vela activa de Kalshi...
                </div>

            </div>

        </div>
        """
    )

    time.sleep(
        REFRESH_SECONDS
    )

    st.rerun()


# ============================================================
# HORARIOS
# ============================================================

ticker = market.get(
    "ticker",
    SERIES,
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

    time.sleep(
        REFRESH_SECONDS
    )

    st.rerun()


# ============================================================
# SEÑAL PRINCIPAL FIJA
# ============================================================

signal = locked_signal(
    ticker,
    open_time.isoformat(),
)

direction = signal["direction"]

model_probability = signal["probability"]

strength = signal["strength"]


# ============================================================
# TIEMPO RESTANTE
# ============================================================

now_utc = datetime.now(
    timezone.utc
)

seconds_left = max(
    0,
    int(
        (
            close_time
            - now_utc
        ).total_seconds()
    ),
)

minutes_left = (
    seconds_left // 60
)

seconds_only = (
    seconds_left % 60
)


# ============================================================
# KALSHI
# ============================================================

kalshi_probability = get_kalshi_probability(
    market
)

kalshi_up = kalshi_probability

kalshi_down = (
    1.0 - kalshi_probability
)

kalshi_direction = (
    "SUBE"
    if kalshi_probability >= 0.50
    else "BAJA"
)


# ============================================================
# TARGET
# ============================================================

target = get_target(
    market
)


# ============================================================
# ENTRADA
# ============================================================

max_entry = max_entry_price(
    model_probability
)

current_entry = kalshi_probability

entry_favorable = (
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

if (
    btc_price is not None
    and target is not None
):

    distance_target = (
        target - btc_price
    )

else:

    distance_target = None


# ============================================================
# CLASES VISUALES
# ============================================================

if direction == "SUBE":

    signal_class = "signal-green"
    signal_icon = "🟢"
    direction_class = "green"

else:

    signal_class = "signal-red"
    signal_icon = "🔴"
    direction_class = "red"


# ============================================================
# LECTURA ACTUAL
# ============================================================

render_html(
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

        <div class="muted center" style="margin-top:10px;">
            Señal fija desde el inicio de esta vela
        </div>

    </div>
    """
)


# ============================================================
# BTC EN VIVO
# ============================================================

render_html(
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
    """
)


# ============================================================
# TARGET / CIERRE
# ============================================================

target_text = money(target)

distance_text = money(
    distance_target
)

projection_text = money(
    projection
)


render_html(
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
                    {projection_text}
                </div>

            </div>

        </div>

    </div>
    """
)


# ============================================================
# KALSHI EN VIVO
# ============================================================

if kalshi_direction == "SUBE":

    kalshi_icon = "🟢"
    kalshi_class = "green"

else:

    kalshi_icon = "🔴"
    kalshi_class = "red"


render_html(
    f"""
    <div class="card">

        <div class="section-title">
            KALSHI EN VIVO
        </div>

        <div class="center">

            <div class="big {kalshi_class}">
                {kalshi_icon} {kalshi_direction}
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
    """
)


# ============================================================
# ALERTA DE GIRO
# ============================================================

turn_detected = (
    kalshi_direction != direction
    and abs(
        kalshi_probability - 0.50
    ) >= 0.07
)


if turn_detected:

    render_html(
        f"""
        <div class="alert">

            🚨 ALERTA DE GIRO

            <br>

            {direction} → {kalshi_direction}

        </div>
        """
    )

else:

    render_html(
        """
        <div class="good">

            📡 RADAR

            <br>

            Sin giro significativo

        </div>
        """
    )


# ============================================================
# ENTRADA
# ============================================================

if entry_favorable:

    entry_status = "FAVORABLE"
    entry_class = "good"

else:

    entry_status = "EN LÍMITE / ESPERAR"
    entry_class = "wait"


render_html(
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
                    Kalshi actual
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

        <div class="{entry_class}">
            {entry_status}
        </div>

    </div>
    """
)


# ============================================================
# PRÓXIMA VELA
# ============================================================

if seconds_left <= PREVIEW_SECONDS:

    next_direction, next_probability, next_strength = (
        calculate_preview(
            history,
            close_time,
        )
    )

    if next_direction == "SUBE":

        next_icon = "🟢"

    else:

        next_icon = "🔴"

    render_html(
        f"""
        <div class="card">

            <div class="section-title">
                PRÓXIMA VELA
            </div>

            <div class="center">

                <div class="big">
                    {next_icon} {next_direction}
                </div>

                <div style="
                    font-size:25px;
                    font-weight:900;
                    margin-top:4px;
                ">
                    {next_probability * 100:.1f}%
                </div>

                <div class="muted">
                    Fuerza: {next_strength}
                </div>

                <div class="muted" style="margin-top:8px;">
                    Vista preliminar.
                    No reemplaza la señal actual.
                </div>

            </div>

        </div>
        """
    )


# ============================================================
# INFORMACIÓN
# ============================================================

render_html(
    """
    <div class="footer">

        Señal principal bloqueada durante toda la vela de 15 minutos.

        <br>

        Kalshi se actualiza en vivo.

        <br>

        PRÓXIMA VELA aparece solamente durante los últimos 3 minutos.

        <br>

        Este bot genera señales y NO ejecuta compras automáticamente.

    </div>
    """
)


# ============================================================
# ACTUALIZACIÓN
# ============================================================

time.sleep(
    REFRESH_SECONDS
)

st.rerun()
