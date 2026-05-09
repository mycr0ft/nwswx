from dataclasses import dataclass, field
from typing import Any

import requests
from shapely import Polygon, Point

BASE_URL = "https://api.weather.gov"

USER_AGENT = "nwswx/0.1.0"


@dataclass
class Alert:
    id: str
    headline: str
    severity: str
    urgency: str
    event: str
    area_desc: str
    raw: dict[str, Any] = field(repr=False)
    polygon: Polygon | None = field(default=None)


def _parse_polygon(coords_str: str | None) -> Polygon | None:
    if not coords_str:
        return None
    points = []
    for pair in coords_str.strip().split():
        lat_str, lon_str = pair.split(",")
        points.append((float(lon_str), float(lat_str)))
    if len(points) < 3:
        return None
    return Polygon(points)


def _parse_alerts(data: dict) -> list[Alert]:
    alerts = []
    for f in data.get("features", []):
        props = f.get("properties", {})
        poly_str = props.get("polygon")
        alerts.append(
            Alert(
                id=props.get("id", ""),
                headline=props.get("headline", ""),
                severity=props.get("severity", ""),
                urgency=props.get("urgency", ""),
                event=props.get("event", ""),
                area_desc=props.get("areaDesc", ""),
                polygon=_parse_polygon(poly_str),
                raw=f,
            )
        )
    return alerts


def get_active_alerts() -> list[Alert]:
    resp = requests.get(f"{BASE_URL}/alerts/active", headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return _parse_alerts(resp.json())


def get_alerts_by_zone(zone_id: str) -> list[Alert]:
    resp = requests.get(
        f"{BASE_URL}/alerts/active/zone/{zone_id}",
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    return _parse_alerts(resp.json())


def get_alerts_by_county(county_id: str) -> list[Alert]:
    resp = requests.get(
        f"{BASE_URL}/alerts/active/county/{county_id}",
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    return _parse_alerts(resp.json())


def get_relevant_alerts(lat: float, lon: float) -> list[Alert]:
    from nwswx.client import get_point

    point = Point(lon, lat)
    pt = get_point(lat, lon)

    seen: set[str] = set()
    relevant: list[Alert] = []

    for alert in get_active_alerts():
        if alert.id in seen:
            continue
        if alert.polygon is not None and alert.polygon.contains(point):
            seen.add(alert.id)
            relevant.append(alert)

    if pt.county_id:
        for alert in get_alerts_by_zone(pt.county_id):
            if alert.id not in seen:
                seen.add(alert.id)
                relevant.append(alert)

    if pt.forecast_zone_id:
        for alert in get_alerts_by_zone(pt.forecast_zone_id):
            if alert.id not in seen:
                seen.add(alert.id)
                relevant.append(alert)

    if pt.fire_weather_zone_id:
        for alert in get_alerts_by_zone(pt.fire_weather_zone_id):
            if alert.id not in seen:
                seen.add(alert.id)
                relevant.append(alert)

    return relevant
