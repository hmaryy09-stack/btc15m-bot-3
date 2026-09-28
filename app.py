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
)

NY = ZoneInfo("America/New_York")

SERIES = "KXBTC15M"

KALSHI_HOSTS = [
    "https://external-api.kalshi.com/trade-api/v2",
    "https://api.elections.kalshi.com/trade-api/v2",
]

REFRESH_SECONDS = 10
PREVIEW_SECONDS = 180
MIN_EXPECTED_RETURN = 0.10
POSITION_SIZE = 25


# ============================================================
# ESTILO — PARECIDO AL BOT 1
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at top right,
                rgba(20,45,75,.35),
                transparent 40%
            ),
            #070b14;
    }

    .block-container {
        max-width: 760px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    .header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 12px;
    }

    .btc-logo {
        width: 54px;
        height: 54px;
        border-radius: 50%;
        background: #f7931a;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 31px;
        font-weight: 900;
    }

    .header-title {
        font-size: 1.65rem;
        font-weight: 850;
        letter-spacing: .5px;
    }

    .header-sub {
        color: #8d96a8;
        font-size: .9rem;
    }

    .live {
        margin-left: auto;
        text-align: right;
        color: #47e889;
        font-size: .9rem;
    }

    .card {
        background: linear-gradient(
            145deg,
            rgba(19,31,52,.96),
            rgba(8,14,26,.98)
        );
        border: 1px solid #253755;
        border-radius: 18px;
        padding: 18px;
        margin: 10px 0;
        box-shadow: 0 8px 30px rgba(0,0,0,.18);
    }

    .card-red {
        border-color: #b63b50;
    }

    .card-green {
        border-color: #27a96b;
    }

    .section-title {
        color: #aeb8ca;
        font-size: .92rem;
        font-weight: 800;
        letter-spacing: .4px;
        margin-bottom: 8px;
    }

    .signal-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
    }

    .signal {
        font-size: 2.35rem;
        font-weight: 900;
        line-height: 1;
    }

    .signal-red {
        color: #ff5964;
    }

    .signal-green {
        color: #47e889;
    }

    .prob {
        font-size: 2.6rem;
        font-weight: 900;
        color: #47e889;
        text-align: right;
    }

    .muted {
        color: #8d96a8;
        font-size: .86rem;
    }

    .price {
        font-size: 1.75rem;
        font-weight: 850;
        margin-top: 8px;
    }

    .mini-card {
        background: #0d1728;
        border: 1px solid #253755;
        border-radius: 15px;
        padding: 14px;
        min-height: 85px;
    }

    .mini-title {
        color: #8d96a8;
        font-size: .75rem;
        text-transform: uppercase;
    }

    .mini-value {
        font-size: 1.35rem;
        font-weight: 850;
        margin-top: 5px;
    }

    .guide-red {
        border: 1px solid #d63e55;
        background: rgba(90,20,35,.20);
        border-radius: 17px;
        padding: 17px;
        margin: 10px 0;
    }

    .guide-green {
        border: 1px solid #28b774;
        background: rgba(15,90,55,.20);
        border-radius: 17px;
        padding: 17px;
        margin: 10px 0;
    }

    .guide-title {
        font-size: 1.35rem;
        font-weight: 900;
    }

    .kalshi-bar {
        height: 26px;
        display: flex;
        overflow: hidden;
        border-radius: 10px;
        margin-top: 12px;
    }

    .bar-up {
        background: #43df89;
        color: #06150d;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
    }

    .bar-down {
        background: #ff5964;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
    }

    .alert {
        background: rgba(100,90,15,.35);
        border: 1px solid #9b8d22;
        border-radius: 16px;
        padding: 15px;
        color: #f0e58b;
        margin: 10px 0;
    }

    .favorable {
        background: rgba(20,105,65,.40);
        border: 1px solid #2ac477;
        color: #72efa6;
        border-radius: 14px;
        padding: 15px;
        font-weight: 800;
        font-size: 1.1rem;
        margin-top: 10px;
    }

    .wait {
        background: rgba(90,80,20,.30);
        border: 1px solid #a69731;
        color: #eee28a;
        border-radius: 14px;
        padding: 15px;
        font-weight: 800;
        margin-top: 10px;
    }

    .next-card {
        background: #111c30;
        border: 1px solid #455b7e;
        border-radius: 16px;
        padding: 16px;
        margin-top: 10px;
    }

    @media (max-width: 600px) {

        .block-container {
            padding-left: .7rem;
            padding-right: .7rem;
        }

        .signal {
            font-size: 2rem;
        }

        .prob {
            font-size: 2.2rem;
        }

        .price {
            font-size: 1.5rem;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# UTILIDADES
# ============================================================

def now_utc():
    return datetime.now(timezone.utc)


def parse_dt(value):

    if not value:
        return None

    try:

        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(
                float(value),
                tz=timezone.utc,
            )

        value = str(value)

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def money(value):

    if value is None:
        return "—"

    return f"${value:,.2f}"


def pct(value):

    if value is None:
        return "—"

    return f"{value * 100:.1f}%"


def countdown(seconds):

    if seconds is None:
        return "—"

    seconds = max(0, int(seconds))

    minutes = seconds // 60
    secs = seconds % 60

    return f"{minutes:02d}:{secs:02d}"


def change_percent(old, new):

    if old is None or new is None or old == 0:
        return 0.0

    return (new - old) / old


# ============================================================
# KRAKEN — BTC
# ============================================================

@st.cache_data(
    ttl=8,
    show_spinner=False,
)
def get_btc_history():

    url = "https://api.kraken.com/0/public/OHLC"

    params = {
        "pair": "XBTUSD",
        "interval": 1,
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("error"):
            return []

        result = data.get(
            "result",
            {},
        )

        pair_key = None

        for key in result:

            if key != "last":
                pair_key = key
                break

        if not pair_key:
            return []

        candles = result[pair_key]

        output = []

        for candle in candles:

            try:

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

            except Exception:
                continue

        return output

    except Exception:

        return []


def price_before(candles, target_time):

    valid = [
        candle
        for candle in candles
        if candle["time"] <= target_time
    ]

    if not valid:
        return None

    return valid[-1]["close"]


def current_btc_price(candles):

    if not candles:
        return None

    return candles[-1]["close"]


# ============================================================
# MODELO
# ============================================================

def calculate_signal(
    candles,
    market_open,
):

    if not candles:
        return None

    # SOLAMENTE información anterior
    # a la apertura de la vela.

    previous = [
        candle
        for candle in candles
        if candle["time"] < market_open
    ]

    if len(previous) < 20:
        return None

    latest = previous[-1]

    latest_time = latest["time"]

    p1 = price_before(
        previous,
        latest_time - timedelta(minutes=1),
    )

    p3 = price_before(
        previous,
        latest_time - timedelta(minutes=3),
    )

    p5 = price_before(
        previous,
        latest_time - timedelta(minutes=5),
    )

    p10 = price_before(
        previous,
        latest_time - timedelta(minutes=10),
    )

    p15 = price_before(
        previous,
        latest_time - timedelta(minutes=15),
    )

    c1 = change_percent(
        p1,
        latest["close"],
    )

    c3 = change_percent(
        p3,
        latest["close"],
    )

    c5 = change_percent(
        p5,
        latest["close"],
    )

    c10 = change_percent(
        p10,
        latest["close"],
    )

    c15 = change_percent(
        p15,
        latest["close"],
    )

    score = (
        c1 * 0.10
        + c3 * 0.20
        + c5 * 0.25
        + c10 * 0.25
        + c15 * 0.20
    )

    probability = (
        0.50
        + abs(score) * 13
    )

    probability = max(
        0.55,
        min(0.84, probability),
    )

    direction = (
        "SUBE"
        if score >= 0
        else "BAJA"
    )

    return {
        "direction": direction,
        "probability": probability,
        "score": score,
        "price": latest["close"],
        "c1": c1,
        "c3": c3,
        "c5": c5,
        "c10": c10,
        "c15": c15,
    }


def strength(probability):

    if probability >= 0.70:
        return "FUERTE"

    if probability >= 0.62:
        return "MEDIA"

    return "BAJA"


# ============================================================
# SEÑAL FIJA POR VELA
# ============================================================

@st.cache_data(
    ttl=900,
    show_spinner=False,
)
def locked_signal(
    ticker,
    open_time_iso,
):

    market_open = parse_dt(
        open_time_iso
    )

    candles = get_btc_history()

    signal = calculate_signal(
        candles,
        market_open,
    )

    if signal is None:

        return {
            "direction": "SUBE",
            "probability": 0.55,
            "score": 0,
            "price": None,
            "c1": 0,
            "c3": 0,
            "c5": 0,
            "c10": 0,
            "c15": 0,
        }

    return signal


# ============================================================
# KALSHI
# ============================================================

def get_markets():

    for host in KALSHI_HOSTS:

        try:

            response = requests.get(
                f"{host}/markets",
                params={
                    "series_ticker": SERIES,
                    "status": "open",
                    "limit": 100,
                },
                timeout=10,
            )

            if response.status_code != 200:
                continue

            data = response.json()

            markets = data.get(
                "markets",
                [],
            )

            if markets:
                return markets

        except Exception:
            continue

    return []


def current_market(markets):

    current = now_utc()

    candidates = []

    for market in markets:

        open_time = parse_dt(
            market.get("open_time")
        )

        close_time = parse_dt(
            market.get("close_time")
        )

        if not open_time or not close_time:
            continue

        if (
            open_time <= current
            < close_time
        ):

            candidates.append(
                (
                    open_time,
                    market,
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    return candidates[0][1]


def next_market(
    markets,
    current_ticker=None,
):

    current = now_utc()

    candidates = []

    for market in markets:

        ticker = market.get(
            "ticker"
        )

        if ticker == current_ticker:
            continue

        open_time = parse_dt(
            market.get("open_time")
        )

        if not open_time:
            continue

        if open_time > current:

            candidates.append(
                (
                    open_time,
                    market,
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0]
    )

    return candidates[0][1]


def kalshi_probability(market):

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
        bid = (
            float(bid)
            if bid is not None
            else None
        )
    except Exception:
        bid = None

    try:
        ask = (
            float(ask)
            if ask is not None
            else None
        )
    except Exception:
        ask = None

    try:
        last = (
            float(last)
            if last is not None
            else None
        )
    except Exception:
        last = None

    if (
        bid is not None
        and ask is not None
    ):

        return (
            bid + ask
        ) / 2

    if last is not None:
        return last

    if bid is not None:
        return bid

    if ask is not None:
        return ask

    return None


def target_price(market):

    for field in [
        "custom_strike",
        "strike",
        "floor_strike",
        "cap_strike",
    ]:

        value = market.get(field)

        if value is not None:

            try:
                return float(value)
            except Exception:
                pass

    return None


# ============================================================
# CONFIRMACIÓN PROGRESIVA
# ============================================================

def progressive_confirmation(
    direction,
    candles,
):

    if not candles:
        return 0

    if len(candles) < 15:
        return 0

    latest = candles[-1]

    checks = 0

    p3 = price_before(
        candles,
        latest["time"]
        - timedelta(minutes=3),
    )

    p5 = price_before(
        candles,
        latest["time"]
        - timedelta(minutes=5),
    )

    p10 = price_before(
        candles,
        latest["time"]
        - timedelta(minutes=10),
    )

    c3 = change_percent(
        p3,
        latest["close"],
    )

    c5 = change_percent(
        p5,
        latest["close"],
    )

    c10 = change_percent(
        p10,
        latest["close"],
    )

    if direction == "SUBE":

        if c3 >= 0:
            checks += 1

        if c5 >= 0:
            checks += 1

        if c10 >= 0:
            checks += 1

    else:

        if c3 <= 0:
            checks += 1

        if c5 <= 0:
            checks += 1

        if c10 <= 0:
            checks += 1

    return checks


# ============================================================
# GUÍA PARA CIERRE
# ============================================================

def projected_close(
    btc,
    remaining_seconds,
    candles,
):

    if btc is None:
        return None, None

    if not candles or len(candles) < 3:
        return btc, 0

    p3 = price_before(
        candles,
        candles[-1]["time"]
        - timedelta(minutes=3),
    )

    if p3 is None:
        return btc, 0

    elapsed_seconds = 180

    velocity = (
        btc - p3
    ) / elapsed_seconds

    projected = (
        btc
        + velocity
        * max(0, remaining_seconds)
    )

    return projected, velocity


# ============================================================
# MEJOR ENTRADA
# ============================================================

def maximum_entry(probability):

    if probability is None:
        return None

    return (
        probability
        / (1 + MIN_EXPECTED_RETURN)
    )


# ============================================================
# HEADER
# ============================================================

def render_header():

    current_ny = datetime.now(NY)

    st.markdown(
        f"""
        <div class="header">

            <div class="btc-logo">₿</div>

            <div>
                <div class="header-title">
                    BTC • 15 MIN
                </div>

                <div class="header-sub">
                    Predictor • Kalshi
                </div>
            </div>

            <div class="live">
                🟢 EN VIVO<br>
                {current_ny.strftime("%I:%M:%S %p")}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DASHBOARD
# ============================================================

@st.fragment(
    run_every=REFRESH_SECONDS
)
def dashboard():

    render_header()

    markets = get_markets()

    if not markets:

        st.error(
            "No se pudieron obtener los mercados de Kalshi."
        )

        return

    market = current_market(
        markets
    )

    if not market:

        st.warning(
            "No hay una vela BTC 15M activa."
        )

        return

    ticker = market.get(
        "ticker",
        ""
    )

    open_time = parse_dt(
        market.get("open_time")
    )

    close_time = parse_dt(
        market.get("close_time")
    )

    if not open_time or not close_time:

        st.error(
            "El mercado no tiene horarios válidos."
        )

        return

    # ========================================================
    # SEÑAL FIJA
    # ========================================================

    signal = locked_signal(
        ticker,
        open_time.isoformat(),
    )

    direction = signal["direction"]
    probability = signal["probability"]

    # ========================================================
    # DATOS EN VIVO
    # ========================================================

    candles = get_btc_history()

    btc = current_btc_price(
        candles
    )

    current = now_utc()

    remaining = (
        close_time - current
    ).total_seconds()

    kalshi_prob = kalshi_probability(
        market
    )

    if kalshi_prob is not None:

        kalshi_up = kalshi_prob
        kalshi_down = (
            1 - kalshi_prob
        )

        kalshi_direction = (
            "SUBE"
            if kalshi_up >= 0.50
            else "BAJA"
        )

    else:

        kalshi_up = None
        kalshi_down = None
        kalshi_direction = None

    target = target_price(
        market
    )

    confirmation = progressive_confirmation(
        direction,
        candles,
    )

    projected, velocity = projected_close(
        btc,
        remaining,
        candles,
    )

    max_entry = maximum_entry(
        probability
    )

    if direction == "SUBE":

        live_direction_price = (
            kalshi_up
        )

    else:

        live_direction_price = (
            kalshi_down
            if kalshi_down is not None
            else None
        )

    # ========================================================
    # ALERTA DE GIRO
    # ========================================================

    if (
        kalshi_direction
        and kalshi_direction != direction
    ):

        st.markdown(
            f"""
            <div class="alert">
                🚨 <b>ALERTA DE GIRO</b><br><br>
                <span style="font-size:1.2rem;">
                {direction} → {kalshi_direction}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # LECTURA ACTUAL
    # ========================================================

    signal_class = (
        "card-green"
        if direction == "SUBE"
        else "card-red"
    )

    signal_icon = (
        "🟢"
        if direction == "SUBE"
        else "🔴"
    )

    signal_color = (
        "signal-green"
        if direction == "SUBE"
        else "signal-red"
    )

    st.markdown(
        f"""
        <div class="card {signal_class}">

            <div class="section-title">
                LECTURA ACTUAL
            </div>

            <div class="signal-row">

                <div>
                    <div class="signal {signal_color}">
                        {signal_icon} {direction}
                    </div>

                    <div class="muted">
                        🔒 Dirección fija
                    </div>
                </div>

                <div>
                    <div class="prob">
                        {probability * 100:.0f}%
                    </div>

                    <div class="muted">
                        probabilidad estimada
                    </div>
                </div>

            </div>

            <div class="price">
                {money(btc)}
            </div>

            <div class="muted">
                Modelo fijo para esta vela
            </div>

            <br>

            <div class="section-title">
                Confirmación progresiva:
                {confirmation}/3
            </div>

            <div style="
                display:flex;
                gap:8px;
                margin-top:8px;
            ">

                <div style="
                    flex:1;
                    height:10px;
                    border-radius:8px;
                    background:
                    {'#43df89' if confirmation >= 1 else '#26354c'};
                "></div>

                <div style="
                    flex:1;
                    height:10px;
                    border-radius:8px;
                    background:
                    {'#43df89' if confirmation >= 2 else '#26354c'};
                "></div>

                <div style="
                    flex:1;
                    height:10px;
                    border-radius:8px;
                    background:
                    {'#43df89' if confirmation >= 3 else '#26354c'};
                "></div>

            </div>

            <div class="mini-card" style="margin-top:12px;">

                🎯 <b>{direction} activa</b><br>

                <span class="muted">
                    La dirección permanece fija
                    durante esta vela.
                </span>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # OBJETIVO + CIERRE
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            f"""
            <div class="mini-card">

                <div class="mini-title">
                    🎯 OBJETIVO KALSHI
                </div>

                <div class="mini-value">
                    {money(target)}
                </div>

                <div class="muted">

                    {
                        f"Distancia: {((target-btc)/btc)*100:+.3f}%"
                        if target is not None and btc
                        else "Distancia: —"
                    }

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:

        st.markdown(
            f"""
            <div class="mini-card">

                <div class="mini-title">
                    ⏱️ CIERRE
                </div>

                <div class="mini-value">
                    {countdown(remaining)}
                </div>

                <div class="muted">
                    Cierre:
                    {close_time.astimezone(NY).strftime("%I:%M %p")}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # GUÍA PARA EL CIERRE
    # ========================================================

    guide_class = (
        "guide-green"
        if direction == "SUBE"
        else "guide-red"
    )

    guide_text = (
        "PROBABLE CIERRE SUBE"
        if direction == "SUBE"
        else "PROBABLE CIERRE BAJA"
    )

    velocity_per_second = (
        velocity
        if velocity is not None
        else 0
    )

    if target is not None and btc is not None:

        required_velocity = (
            target - btc
        ) / max(
            remaining,
            1,
        )

    else:

        required_velocity = 0

    st.markdown(
        f"""
        <div class="{guide_class}">

            <div class="section-title">
                GUÍA PARA EL CIERRE
            </div>

            <div class="guide-title">
                {guide_text}
                &nbsp;&nbsp;
                {probability * 100:.0f}%
            </div>

            <div class="muted">
                El cálculo usa el precio,
                movimiento reciente y ritmo actual.
            </div>

            <br>

            <div style="
                display:flex;
                gap:8px;
            ">

                <div class="mini-card"
                     style="flex:1;">

                    <div class="mini-title">
                        CIERRE PROYECTADO
                    </div>

                    <div class="mini-value">
                        {money(projected)}
                    </div>

                </div>

                <div class="mini-card"
                     style="flex:1;">

                    <div class="mini-title">
                        RITMO ACTUAL
                    </div>

                    <div class="mini-value">
                        {velocity_per_second:+.2f} $/s
                    </div>

                </div>

                <div class="mini-card"
                     style="flex:1;">

                    <div class="mini-title">
                        RITMO NECESARIO
                    </div>

                    <div class="mini-value">
                        {required_velocity:+.2f} $/s
                    </div>

                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # KALSHI EN VIVO
    # ========================================================

    st.markdown(
        """
        <div class="card">

            <div class="section-title">
                📊 KALSHI EN VIVO
            </div>

        """,
        unsafe_allow_html=True,
    )

    if kalshi_prob is not None:

        st.markdown(
            f"""
            <div style="
                display:flex;
                justify-content:space-between;
                font-size:1.15rem;
                font-weight:800;
            ">

                <span>
                    🟢 SUBE {kalshi_up*100:.0f}%
                </span>

                <span>
                    🔴 BAJA {kalshi_down*100:.0f}%
                </span>

            </div>

            <div class="kalshi-bar">

                <div class="bar-up"
                     style="width:{kalshi_up*100}%">

                    {kalshi_up*100:.0f}%

                </div>

                <div class="bar-down"
                     style="width:{kalshi_down*100}%">

                    {kalshi_down*100:.0f}%

                </div>

            </div>

            <br>

            Dirección en vivo:
            <b>{kalshi_direction}</b>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.write(
            "Kalshi no tiene precio disponible."
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # MEJOR ENTRADA
    # ========================================================

    st.markdown(
        """
        <div class="card">

            <div class="section-title">
                💰 MEJOR ENTRADA
            </div>

        """,
        unsafe_allow_html=True,
    )

    st.write(
        f"Probabilidad modelo: "
        f"**{probability*100:.1f}%**"
    )

    if max_entry is not None:

        st.write(
            f"Entrada máxima sugerida: "
            f"**{max_entry*100:.1f}¢**"
        )

    if live_direction_price is not None:

        st.write(
            f"Precio actual de dirección: "
            f"**{live_direction_price*100:.1f}¢**"
        )

        if (
            max_entry is not None
            and live_direction_price
            <= max_entry
        ):

            st.markdown(
                """
                <div class="favorable">
                    ✅ ENTRADA FAVORABLE
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                """
                <div class="wait">
                    ⏳ ESPERAR MEJOR PRECIO
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # TAMAÑO
    # ========================================================

    st.markdown(
        f"""
        <div class="card">

            <div class="section-title">
                📊 TAMAÑO SUGERIDO
            </div>

            <div style="
                font-size:1.45rem;
                font-weight:850;
            ">
                {POSITION_SIZE}% del capital
            </div>

            <div class="muted">
                Sugerencia de gestión de riesgo.
                No realiza ninguna compra.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # RADAR
    # ========================================================

    st.markdown(
        """
        <div class="card">

            <div class="section-title">
                🚨 RADAR TEMPRANO
            </div>
        """,
        unsafe_allow_html=True,
    )

    if (
        kalshi_direction
        and kalshi_direction != direction
    ):

        st.warning(
            f"Kalshi está mostrando "
            f"**{kalshi_direction}** mientras "
            f"la señal fija es **{direction}**."
        )

    else:

        st.success(
            "Sin giro significativo."
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # PRÓXIMA VELA
    # ========================================================

    if remaining <= PREVIEW_SECONDS:

        nxt = next_market(
            markets,
            ticker,
        )

        if nxt:

            nxt_ticker = nxt.get(
                "ticker"
            )

            nxt_open = parse_dt(
                nxt.get("open_time")
            )

            if nxt_ticker and nxt_open:

                nxt_signal = locked_signal(
                    nxt_ticker,
                    nxt_open.isoformat(),
                )

                if nxt_signal:

                    st.markdown(
                        f"""
                        <div class="next-card">

                            <div class="section-title">
                                🔮 PRÓXIMA VELA
                            </div>

                            <div style="
                                font-size:1.35rem;
                                font-weight:850;
                            ">

                                {
                                    '🟢 SUBE'
                                    if nxt_signal['direction'] == 'SUBE'
                                    else '🔴 BAJA'
                                }

                                &nbsp;&nbsp;

                                {nxt_signal['probability']*100:.0f}%

                            </div>

                            <div class="muted">
                                Preliminar.
                                Se activa cuando comience
                                la nueva vela.
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ========================================================
    # INFORMACIÓN
    # ========================================================

    st.markdown(
        f"""
        <div style="
            text-align:center;
            color:#78849a;
            font-size:.78rem;
            margin-top:15px;
        ">

            Mercado: {ticker}<br>

            Actualización automática cada
            {REFRESH_SECONDS} segundos<br>

            🟢 Señales solamente •
            Sin compras automáticas

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# EJECUTAR
# ============================================================

dashboard()
