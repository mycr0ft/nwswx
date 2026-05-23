from dataclasses import dataclass, field
from typing import Any

import requests

from nwswx.exceptions import NwsApiError

BASE_URL = "https://api.weather.gov"
REQUEST_TIMEOUT = 15


@dataclass
class NwsPoint:
    lat: float
    lon: float
    raw: dict[str, Any] = field(repr=False)
    grid_id: str = ""
    grid_x: int = 0
    grid_y: int = 0
    forecast_url: str = ""
    forecast_hourly_url: str = ""
    forecast_grid_data_url: str = ""
    city: str = ""
    state: str = ""
    county_id: str = ""
    forecast_zone_id: str = ""
    fire_weather_zone_id: str = ""
    distance: float = 0.0
    bearing: int = 0


def _extract_id(url: str) -> str:
    return url.rstrip("/").split("/")[-1] if url else ""


def get_point(lat: float, lon: float) -> NwsPoint:
    url = f"{BASE_URL}/points/{lat},{lon}"
    try:
        resp = requests.get(url, headers={"User-Agent": "nwswx/0.1.0"}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise NwsApiError(f"Failed to get location data from NWS: {e}") from e
    data = resp.json()
    props = data["properties"]

    return NwsPoint(
        lat=lat,
        lon=lon,
        raw=data,
        grid_id=props["gridId"],
        grid_x=props["gridX"],
        grid_y=props["gridY"],
        forecast_url=props.get("forecast", ""),
        forecast_hourly_url=props.get("forecastHourly", ""),
        forecast_grid_data_url=props.get("forecastGridData", ""),
        city=props.get("relativeLocation", {}).get("properties", {}).get("city", ""),
        state=props.get("relativeLocation", {}).get("properties", {}).get("state", ""),
        county_id=_extract_id(props.get("county", "")),
        forecast_zone_id=_extract_id(props.get("forecastZone", "")),
        fire_weather_zone_id=_extract_id(props.get("fireWeatherZone", "")),
        distance=props.get("relativeLocation", {}).get("properties", {}).get("distance", {}).get("value", 0.0),
        bearing=props.get("relativeLocation", {}).get("properties", {}).get("bearing", {}).get("value", 0),
    )
