from dataclasses import dataclass, field
from typing import Any

import requests

from nwswx.client import NwsPoint

BASE_URL = "https://api.weather.gov"


@dataclass
class ForecastPeriod:
    number: int
    name: str
    start_time: str
    end_time: str
    is_daytime: bool
    temperature: int
    temperature_unit: str
    temperature_trend: str | None
    wind_speed: str
    wind_direction: str
    icon: str
    short_forecast: str
    detailed_forecast: str
    probability_of_precipitation: float | None = 0.0


@dataclass
class Forecast:
    raw: dict[str, Any] = field(repr=False)
    updated: str = ""
    periods: list[ForecastPeriod] = field(default_factory=list)


@dataclass
class DaySummary:
    day_name: str
    high: int | None
    low: int | None
    conditions: str
    symbol: str
    pop: float | None


_WEATHER_SYMBOLS = [
    ("thunderstorm", "⛈️"),
    ("sunny", "☀️"),
    ("clear", "☀️"),
    ("mostly sunny", "🌤️"),
    ("mostly clear", "🌤️"),
    ("partly cloudy", "⛅"),
    ("mostly cloudy", "🌥️"),
    ("cloudy", "☁️"),
    ("rain", "🌧️"),
    ("shower", "🌧️"),
    ("drizzle", "🌧️"),
    ("snow", "❄️"),
    ("flurry", "❄️"),
    ("blizzard", "❄️"),
    ("fog", "🌫️"),
    ("haze", "🌫️"),
    ("mist", "🌫️"),
    ("wind", "💨"),
]


def _weather_symbol(short_forecast: str) -> str:
    s = short_forecast.lower()
    priority = _WEATHER_SYMBOLS[:]
    priority.sort(key=lambda x: -len(x[0]))
    for kw, sym in priority:
        if kw in s:
            return sym
    return "☀️"


def summarize_forecast(fc: Forecast, days: int = 3) -> list[DaySummary]:
    summaries = []
    i = 0
    while i < len(fc.periods) and len(summaries) < days:
        day = fc.periods[i]
        if not day.is_daytime:
            summaries.append(
                DaySummary(
                    day_name=day.name,
                    high=None,
                    low=day.temperature,
                    conditions=day.short_forecast,
                    symbol=_weather_symbol(day.short_forecast),
                    pop=day.probability_of_precipitation,
                )
            )
            i += 1
            continue
        night = fc.periods[i + 1] if i + 1 < len(fc.periods) else None
        pops = [p for p in [day.probability_of_precipitation, night.probability_of_precipitation if night else None] if p is not None]
        summaries.append(
            DaySummary(
                day_name=day.name,
                high=day.temperature,
                low=night.temperature if night else None,
                conditions=day.short_forecast,
                symbol=_weather_symbol(day.short_forecast),
                pop=max(pops) if pops else None,
            )
        )
        i += 2
    return summaries


def _parse_periods(periods: list[dict]) -> list[ForecastPeriod]:
    return [
        ForecastPeriod(
            number=p["number"],
            name=p["name"],
            start_time=p["startTime"],
            end_time=p["endTime"],
            is_daytime=p["isDaytime"],
            temperature=p["temperature"],
            temperature_unit=p["temperatureUnit"],
            temperature_trend=p.get("temperatureTrend"),
            wind_speed=p["windSpeed"],
            wind_direction=p["windDirection"],
            icon=p["icon"],
            short_forecast=p["shortForecast"],
            detailed_forecast=p.get("detailedForecast", ""),
            probability_of_precipitation=p.get("probabilityOfPrecipitation", {}).get("value"),
        )
        for p in periods
    ]


def get_forecast(point: NwsPoint) -> Forecast:
    resp = requests.get(point.forecast_url, headers={"User-Agent": "nwswx/0.1.0"})
    resp.raise_for_status()
    data = resp.json()
    props = data["properties"]
    return Forecast(
        raw=data,
        updated=props.get("updated", ""),
        periods=_parse_periods(props.get("periods", [])),
    )


def get_hourly_forecast(point: NwsPoint) -> Forecast:
    resp = requests.get(point.forecast_hourly_url, headers={"User-Agent": "nwswx/0.1.0"})
    resp.raise_for_status()
    data = resp.json()
    props = data["properties"]
    return Forecast(
        raw=data,
        updated=props.get("updated", ""),
        periods=_parse_periods(props.get("periods", [])),
    )
