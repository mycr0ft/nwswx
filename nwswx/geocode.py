import time
from dataclasses import dataclass, field
from typing import Any

import requests
from requests import HTTPError

GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/address"
BENCHMARK = "Public_AR_Current"
VINTAGE = "Current_Current"
USER_AGENT = "nwswx/0.1.0"
MAX_RETRIES = 3
BASE_DELAY = 1.0


class GeocodeError(Exception):
    pass


@dataclass
class GeocodeResult:
    lat: float
    lon: float
    matched_address: str
    raw: dict[str, Any] = field(repr=False)


def geocode(street: str, city: str, state: str, zipcode: str = "") -> GeocodeResult | None:
    params = {
        "street": street,
        "city": city,
        "state": state,
        "benchmark": BENCHMARK,
        "vintage": VINTAGE,
        "format": "json",
    }
    if zipcode:
        params["zip"] = zipcode

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(GEOCODER_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            matches = data.get("result", {}).get("addressMatches", [])
            if not matches:
                return None

            best = matches[0]
            coords = best.get("coordinates", {})
            return GeocodeResult(
                lat=coords["y"],
                lon=coords["x"],
                matched_address=best.get("matchedAddress", ""),
                raw=data,
            )

        except HTTPError as e:
            last_error = e
            status = e.response.status_code
            if 500 <= status < 600 and attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2**attempt)
                time.sleep(delay)
                continue
            raise GeocodeError(f"Census Geocoder returned {status}") from e

        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_DELAY * (2**attempt))
                continue
            raise GeocodeError("Could not reach Census Geocoder") from e

    raise GeocodeError("Geocoding failed") from last_error
