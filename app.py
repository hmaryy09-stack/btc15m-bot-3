 import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="BTC 15 MIN Predictor",
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
# KALSHI
# ============================================================

@st.cache_data(ttl=8)
def get_markets():
    for host in KALSHI_HOSTS:
        try:
            response = requests.get(
                host + "/markets",
                params={
                    "series_ticker": SERIES,
                    "status": "open",
                    "limit": 100,
                },
                timeout=8,
                headers={
                    "User-Agent": "BTC15M-Predictor/1.0"
                },
            )

            if response.ok:
                data = response.json()
                return data.get("markets", [])

        except Exception:
            pass

    return []


def parse_time(value):
    if value is None:
        return None

    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(
                value,
                tz=timezone.utc
            )

        text = str(value).replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def current_market():
    now = datetime.now(timezone.utc)

    candidates = []

    for market in get_markets():

        opened = parse_time(
            market.get("open_time")
        )

        closed = parse_time(
            market.get("close_time")
        )

        if not opened or not closed:
            continue

        if opened <= now < closed:
            candidates.append(
                (opened, closed, market)
            )

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])

    return candidates[0][2]


def next_market():
    now = datetime.now(timezone.utc)

    candidates = []

    for market in get_markets():

        opened = parse_time(
            market.get("open_time")
        )

        if opened and opened > now:
            candidates.append(
                (opened, market)
            )

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])

    return candidates[0][1]


def get_target(market):

    if not market:
        return None

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

            bid = float(bid)
            ask = float(ask)

            if 0 <= bid <= 1 and 0 <= ask <= 1:
                return (bid + ask) / 2

        if last is not None:

            last = float(last)

            if 0 <= last <= 1:
                return last

    except Exception:
        pass

    return None


# ============================================================
# BITCOIN
# ============================================================

@st.cache_data(ttl=8)
def get_btc_price():

    try:

        response = requests.get(
            "https://api.kraken.com/0/public/Ticker",
            params={
                "pair": "XBTUSD"
            },
            timeout=8,
        )

        data = response.json()

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

        response = requests.get(
            "https://api.kraken.com/0/public/OHLC",
            params={
                "pair": "XBTUSD",
                "interval": 1,
            },
            timeout=8,
        )

        data = response.json()

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

        rows = result[key]

        candles = []

        for row in rows:

            candles.append(
                {
                    "time": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                }
            )

        return candles

    except Exception:
        return []


def candles_before_open(open_time):

    if not open_time:
        return []

    open_timestamp = open_time.timestamp()

    candles = get_btc_candles()

    return [
        candle
        for candle in candles
        if candle["time"] < open_timestamp
    ]


# ============================================================
# MODELO FIJO
# ============================================================

@st.cache_data(ttl=900)
def fixed_signal(open_time_key, target):

    try:

        open_time = datetime.fromtimestamp(
            float(open_time_key),
            tz=timezone.utc,
        )

    except Exception:

        return {
            "direction": "SUBE",
            "probability": 0.55,
            "strength": 1,
        }

    candles = candles_before_open(
        open_time
    )

    if len(candles) < 16:

        return {
            "direction": "SUBE",
            "probability": 0.55,
            "strength": 1,
        }

    closes = [
        candle["close"]
        for candle in candles
    ]

    last = closes[-1]

    def return_from(minutes):

        if len(closes) <= minutes:
            return 0

        previous = closes[-1 - minutes]

        if previous == 0:
            return 0

        return (
            last / previous
        ) - 1

    r1 = return_from(1)
    r3 = return_from(3)
    r5 = return_from(5)
    r10 = return_from(10)
    r15 = return_from(15)

    momentum = (
        r1 * 0.30
        + r3 * 0.25
        + r5 * 0.20
        + r10 * 0.15
        + r15 * 0.10
    )

    target_bias = 0

    if target and last:

        distance = (
            last - target
        ) / last

        target_bias = max(
            -0.003,
            min(
                0.003,
                distance * 0.15
            )
        )

    score = momentum + target_bias

    direction = (
        "SUBE"
        if score >= 0
        else "BAJA"
    )

    strength_value = abs(score) * 700

    probability = (
        0.55
        + min(
            0.29,
            strength_value
        )
    )

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
    }


# ============================================================
# UTILIDADES
# ============================================================

def money(value):

    if value is None:
        return "—"

    return f"${value:,.2f}"


def percent(value):

    if value is None:
        return "—"

    return f"{value * 100:.0f}%"


def percent3(value):

    if value is None:
        return "—"

    return f"{value * 100:.3f}%"


def time_ny(value):

    if not value:
        return "—"

    return value.astimezone(
        NY
    ).strftime("%-I:%M %p")


def countdown(close_time):

    if not close_time:
        return "—"

    now = datetime.now(
        timezone.utc
    )

    seconds = max(
        0,
        int(
            (
                close_time - now
            ).total_seconds()
        ),
    )

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    return (
        f"{minutes:02d}:"
        f"{remaining_seconds:02d}"
    )


def max_entry(probability):

    if probability is None:
        return None

    return (
        probability
        / (1 + MIN_EXPECTED_RETURN)
    )


def live_direction(probability):

    if probability is None:
        return "—"

    if probability >= 0.50:
        return "SUBE"

    return "BAJA"


# ============================================================
# DATOS
# ============================================================

market = current_market()

btc = get_btc_price()

kalshi = get_kalshi_probability(
    market
)

target = get_target(
    market
)

if market:

    open_time = parse_time(
        market.get("open_time")
    )

    close_time = parse_time(
        market.get("close_time")
    )

else:

    open_time = None
    close_time = None


# ============================================================
# SEÑAL FIJA
# ============================================================

if open_time:

    signal = fixed_signal(
        str(open_time.timestamp()),
        target,
    )

else:

    signal = {
        "direction": "SUBE",
        "probability": 0.55,
        "strength": 1,
    }


direction = signal[
    "direction"
]

probability = signal[
    "probability"
]

strength = signal[
    "strength"
]


# ============================================================
# CAMBIO DEL BTC
# ============================================================

btc_change = None

if btc:

    historical = candles_before_open(
        open_time
    )

    if historical:

        reference = historical[-1][
            "close"
        ]

        if reference:

            btc_change = (
                btc / reference
            ) - 1


# ============================================================
# KALSHI EN VIVO
# ============================================================

if kalshi is None:

    live_up = 0.50

else:

    live_up = kalshi

live_down = 1 - live_up

live_dir = live_direction(
    kalshi
)


# ============================================================
# DISTANCIA AL OBJETIVO
# ============================================================

if btc and target:

    target_distance = (
        btc - target
    ) / target

else:

    target_distance = None


# ============================================================
# PROYECCIÓN
# ============================================================

if btc and close_time:

    now = datetime.now(
        timezone.utc
    )

    remaining_seconds = max(
        0,
        (
            close_time - now
        ).total_seconds()
    )

else:

    remaining_seconds = 0


if btc:

    if direction == "SUBE":

        projected = btc * (
            1
            + 0.010
            * min(
                1,
                remaining_seconds / 900
            )
        )

    else:

        projected = btc * (
            1
            - 0.010
            * min(
                1,
                remaining_seconds / 900
            )
        )

else:

    projected = None


# ============================================================
# RITMO
# ============================================================

candles = get_btc_candles()

if len(candles) >= 6:

    recent_price = candles[-6][
        "close"
    ]

    current_price = candles[-1][
        "close"
    ]

    actual_seconds = 5 * 60

    current_rate = (
        (
            current_price
            - recent_price
        )
        / actual_seconds
    )

else:

    current_rate = 0


if btc and projected and remaining_seconds > 0:

    required_rate = (
        projected - btc
    ) / remaining_seconds

else:

    required_rate = 0


# ============================================================
# RADAR
# ============================================================

if kalshi is None:

    radar = (
        "Esperando lectura en vivo "
        "de Kalshi."
    )

else:

    difference = abs(
        kalshi - probability
    )

    if difference >= 0.15:

        radar = (
            "⚠️ Kalshi está bastante "
            "separado de la lectura "
            "del modelo."
        )

    elif difference >= 0.08:

        radar = (
            "👀 Hay una diferencia "
            "relevante entre modelo "
            "y Kalshi."
        )

    else:

        radar = (
            "✅ Kalshi permanece "
            "relativamente alineado "
            "con el modelo."
        )


# ============================================================
# PRÓXIMA VELA
# ============================================================

next_preview = None

if close_time:

    seconds_left = (
        close_time
        - datetime.now(timezone.utc)
    ).total_seconds()

else:

    seconds_left = 99999


if seconds_left <= PREVIEW_SECONDS:

    upcoming = next_market()

    if upcoming:

        next_open = parse_time(
            upcoming.get("open_time")
        )

        next_target = get_target(
            upcoming
        )

        if next_open:

            preview = fixed_signal(
                str(
                    next_open.timestamp()
                ),
                next_target,
            )

            next_preview = preview


# ============================================================
# HTML
# ============================================================

signal_color = (
    "#42ef9a"
    if direction == "SUBE"
    else "#ff5961"
)

signal_icon = (
    "▲"
    if direction == "SUBE"
    else "▼"
)

guide_text = (
    f"PROBABLE CIERRE {direction}"
)

change_text = "—"

if btc_change is not None:

    change_text = (
        f"{btc_change * 100:+.2f}%"
    )

change_color = (
    "#42ef9a"
    if btc_change is not None
    and btc_change >= 0
    else "#ff5961"
)

bar1 = "#42ef9a" if strength >= 1 else "#26334a"
bar2 = "#42ef9a" if strength >= 2 else "#26334a"
bar3 = "#42ef9a" if strength >= 3 else "#26334a"

max_entry_value = max_entry(
    probability
)

preview_html = ""

if next_preview:

    preview_color = (
        "#42ef9a"
        if next_preview["direction"]
        == "SUBE"
        else "#ff5961"
    )

    preview_html = f"""
    <div class="card preview">

        <div class="small-title">
            🔮 PRÓXIMA VELA
        </div>

        <div class="preview-value"
             style="color:{preview_color};">

            {next_preview["direction"]}
            · {percent(next_preview["probability"])}

        </div>

        <div class="small-sub">
            Vista previa. No modifica
            la dirección actual.
        </div>

    </div>
    """


html = f"""
<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width,
               initial-scale=1.0">

<style>

* {{
    box-sizing: border-box;
}}

body {{

    margin: 0;

    padding: 8px 6px 28px;

    background:
        radial-gradient(
            circle at top,
            #111b2c 0%,
            #070b14 48%,
            #05070d 100%
        );

    color: #f5f7fb;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

}}

.wrapper {{

    width: 100%;

    max-width: 760px;

    margin: auto;

}}

.topbar {{

    display: flex;

    justify-content:
        space-between;

    align-items: center;

    gap: 10px;

    padding: 6px 5px 13px;

}}

.brand {{

    display: flex;

    align-items: center;

    gap: 10px;

}}

.btc-icon {{

    width: 48px;

    height: 48px;

    min-width: 48px;

    border-radius: 50%;

    background: #f7931a;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 29px;

    font-weight: 900;

}}

.title {{

    font-size: 24px;

    font-weight: 900;

    line-height: 1;

}}

.subtitle {{

    margin-top: 5px;

    color: #8996aa;

    font-size: 14px;

}}

.live {{

    text-align: right;

    color: #42ef9a;

    font-size: 13px;

    font-weight: 800;

    line-height: 1.35;

}}

.dot {{

    display: inline-block;

    width: 10px;

    height: 10px;

    border-radius: 50%;

    background: #42ef9a;

    box-shadow:
        0 0 12px
        rgba(66,239,154,.8);

}}

.card {{

    background:
        linear-gradient(
            145deg,
            #111a2a,
            #0b111d
        );

    border: 1px solid #263653;

    border-radius: 22px;

    padding: 17px;

    margin: 11px 0;

    box-shadow:
        0 10px 30px
        rgba(0,0,0,.22);

}}

.section-title {{

    color: #aeb9cb;

    font-size: 15px;

    font-weight: 900;

    margin-bottom: 11px;

}}

.signal-row {{

    display: flex;

    justify-content:
        space-between;

    align-items: center;

    gap: 10px;

}}

.signal {{

    color: {signal_color};

    font-size: 40px;

    font-weight: 950;

    line-height: 1;

}}

.locked {{

    color: #9aa6b8;

    font-size: 13px;

    margin-top: 8px;

}}

.price {{

    font-size: 30px;

    font-weight: 900;

    margin-top: 14px;

}}

.change {{

    color: {change_color};

    font-size: 15px;

    font-weight: 800;

    margin-top: 2px;

}}

.prob {{

    text-align: right;

}}

.prob-number {{

    color: #42ef9a;

    font-size: 43px;

    font-weight: 950;

    line-height: 1;

}}

.prob-label {{

    color: #8996aa;

    font-size: 13px;

    margin-top: 5px;

}}

.confirm {{

    color: #d9e1ec;

    font-size: 15px;

    font-weight: 800;

    margin-top: 20px;

}}

.bars {{

    display: flex;

    gap: 8px;

    margin-top: 9px;

}}

.bar {{

    height: 13px;

    flex: 1;

    border-radius: 10px;

}}

.notice {{

    background: #14243b;

    border-radius: 15px;

    padding: 12px 14px;

    margin-top: 14px;

}}

.notice-title {{

    font-size: 15px;

    font-weight: 900;

}}

.notice-text {{

    color: #8996aa;

    font-size: 13px;

   
