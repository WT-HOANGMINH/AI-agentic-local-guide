
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx


# =========================================================
# CONFIGURATION
# =========================================================

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

DANANG_LATITUDE = 16.0544
DANANG_LONGITUDE = 108.2022

API_URL = "https://api.open-meteo.com/v1/forecast"

CACHE_TTL = 30 * 60
MAX_STALE = 6 * 3600

MAX_RETRIES = 3
REQUEST_TIMEOUT = 10.0

HOURLY_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation_probability",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "uv_index",
]

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
    "wind_gusts_10m_max",
    "uv_index_max",
]

_cache = {}
_lock = threading.Lock()


# =========================================================
# HTTP REQUEST
# =========================================================

def _call_api(lat: float, lon: float, days: int) -> dict:

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": ",".join(DAILY_FIELDS),
        "timezone": "Asia/Ho_Chi_Minh",
        "forecast_days": days,
    }

    last_error = None

    for attempt in range(MAX_RETRIES):

        try:
            response = httpx.get(
                API_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            hourly = data.get("hourly")
            daily = data.get("daily")

            if not isinstance(hourly, dict) or not isinstance(daily, dict):
                raise ValueError("Invalid hourly/daily response")

            if "time" not in hourly or "time" not in daily:
                raise ValueError("Missing forecast time data")

            return data

        except (httpx.HTTPError, ValueError) as exc:

            last_error = exc

            if attempt < MAX_RETRIES - 1:
                time.sleep(0.5 * (2 ** attempt))

    raise RuntimeError(
        "Unable to retrieve weather forecast"
    ) from last_error


# =========================================================
# DATA NORMALIZATION
# =========================================================

def _normalize(data: dict) -> dict:

    hourly = data["hourly"]
    daily = data["daily"]

    def pick(block, key, index):

        values = block.get(key)

        if not isinstance(values, list):
            return None

        if index >= len(values):
            return None

        return values[index]

    # -----------------------------------------------------
    # HOURLY FORECAST
    # -----------------------------------------------------

    hours = []

    for i, forecast_time in enumerate(hourly["time"]):

        hours.append({
            "time": forecast_time,
            "temp_c": pick(hourly, "temperature_2m", i),
            "feels_like_c": pick(hourly, "apparent_temperature", i),
            "humidity": pick(hourly, "relative_humidity_2m", i),
            "rain_prob": pick(hourly, "precipitation_probability", i),
            "rain_mm": pick(hourly, "precipitation", i),
            "weather_code": pick(hourly, "weather_code", i),
            "wind_kmh": pick(hourly, "wind_speed_10m", i),
            "gust_kmh": pick(hourly, "wind_gusts_10m", i),
            "wind_dir": pick(hourly, "wind_direction_10m", i),
            "uv": pick(hourly, "uv_index", i),
        })

    # -----------------------------------------------------
    # DAILY FORECAST
    # -----------------------------------------------------

    daily_forecast = []

    for i, forecast_date in enumerate(daily["time"]):

        daily_forecast.append({
            "date": forecast_date,
            "weather_code": pick(daily, "weather_code", i),
            "temp_max": pick(daily, "temperature_2m_max", i),
            "temp_min": pick(daily, "temperature_2m_min", i),
            "rain_prob_max": pick(
                daily, "precipitation_probability_max", i
            ),
            "rain_sum_mm": pick(daily, "precipitation_sum", i),
            "gust_max_kmh": pick(daily, "wind_gusts_10m_max", i),
            "uv_max": pick(daily, "uv_index_max", i),
        })

    # -----------------------------------------------------
    # CHECK MISSING FIELDS
    # -----------------------------------------------------

    def find_missing(rows):

        return sorted({
            key
            for row in rows
            for key, value in row.items()
            if value is None
        })

    hourly_missing = find_missing(hours)
    daily_missing = find_missing(daily_forecast)

    return {
        "hours": hours,
        "daily": daily_forecast,
        "hourly_unavailable_fields": hourly_missing,
        "daily_unavailable_fields": daily_missing,
        "unavailable_fields": sorted(
            set(hourly_missing + daily_missing)
        ),
    }


# =========================================================
# CACHE MANAGEMENT
# =========================================================

def _get_cache(key):

    with _lock:
        return _cache.get(key)


def _save_cache(key, payload):

    with _lock:
        _cache[key] = {
            "ts": time.monotonic(),
            "payload": payload,
        }


# =========================================================
# MAIN WEATHER SERVICE
# =========================================================

def get_weather_forecast(
    latitude: float = DANANG_LATITUDE,
    longitude: float = DANANG_LONGITUDE,
    forecast_days: int = 3,
) -> dict:

    """
    Get real weather forecasts from Open-Meteo.

    Features:
        - Hourly forecast
        - Daily forecast
        - Rain probability
        - Temperature and humidity
        - Wind speed and gusts
        - UV index
        - Cache for 30 minutes
        - Retry mechanism
        - Stale cache fallback up to 6 hours

    Default location: Da Nang, Vietnam.
    """

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not isinstance(forecast_days, int) or not 1 <= forecast_days <= 7:
        raise ValueError("forecast_days must be between 1 and 7")

    if not -90 <= latitude <= 90:
        raise ValueError("Invalid latitude")

    if not -180 <= longitude <= 180:
        raise ValueError("Invalid longitude")

    # -----------------------------------------------------
    # CACHE LOOKUP
    # -----------------------------------------------------

    key = (
        round(latitude, 3),
        round(longitude, 3),
        forecast_days,
    )

    now = time.monotonic()

    cached = _get_cache(key)

    if cached:

        age = now - cached["ts"]

        if age < CACHE_TTL:

            return {
                **cached["payload"],
                "is_stale": False,
                "from_cache": True,
                "cache_age_seconds": int(age),
            }

    # -----------------------------------------------------
    # FETCH REAL WEATHER DATA
    # -----------------------------------------------------

    try:

        raw_data = _call_api(
            latitude,
            longitude,
            forecast_days,
        )

        payload = _normalize(raw_data)

        payload.update({
            "source": "Open-Meteo",
            "location": "Da Nang, Vietnam",
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "Asia/Ho_Chi_Minh",
            "fetched_at": datetime.now(TZ).isoformat(
                timespec="minutes"
            ),
            "official_alerts_available": False,
            "forecast_days": forecast_days,
        })

        _save_cache(key, payload)

        return {
            **payload,
            "is_stale": False,
            "from_cache": False,
            "cache_age_seconds": 0,
        }

    # -----------------------------------------------------
    # FALLBACK: USE OLD CACHE
    # -----------------------------------------------------

    except RuntimeError:

        if cached:

            age = time.monotonic() - cached["ts"]

            if age < MAX_STALE:

                return {
                    **cached["payload"],
                    "is_stale": True,
                    "from_cache": True,
                    "cache_age_seconds": int(age),
                    "stale_minutes": int(age / 60),
                }

        raise RuntimeError(
            "Weather API unavailable and no valid cache exists"
        )
