
import httpx


# Tọa độ trung tâm tham khảo của thành phố Đà Nẵng
DANANG_LATITUDE = 16.0544
DANANG_LONGITUDE = 108.2022


def get_weather_forecast(
    latitude: float = DANANG_LATITUDE,
    longitude: float = DANANG_LONGITUDE,
    forecast_days: int = 3,
):
    """
    Lấy dự báo thời tiết từ Open-Meteo.
    Mặc định lấy dự báo cho Đà Nẵng trong 3 ngày.
    """

    if not 1 <= forecast_days <= 7:
        raise ValueError("forecast_days must be between 1 and 7")

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "precipitation_sum",
        ],
        "timezone": "Asia/Ho_Chi_Minh",
        "forecast_days": forecast_days,
    }

    try:
        response = httpx.get(
            url,
            params=params,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()

        return {
            "location": "Da Nang, Vietnam",
            "forecast": data.get("daily", {}),
            "source": "Open-Meteo",
        }

    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Unable to retrieve weather forecast"
        ) from exc
