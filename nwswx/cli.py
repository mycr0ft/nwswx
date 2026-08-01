import argparse
import json
import os
import sys

from nwswx.alerts import get_relevant_alerts
from nwswx.client import get_point
from nwswx.exceptions import NwsApiError
from nwswx.forecast import get_forecast, summarize_forecast
from nwswx.geocode import GeocodeError, geocode

CONFIG_DIR = os.path.expanduser("~/.config/nwswx.json")


def _load_config() -> dict:
    try:
        with open(CONFIG_DIR) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(lat: float, lon: float, celsius: bool = False) -> None:
    os.makedirs(os.path.dirname(CONFIG_DIR), exist_ok=True)
    data = _load_config()
    data.update({"lat": lat, "lon": lon})
    if celsius:
        data["celsius"] = True
    elif "celsius" in data:
        del data["celsius"]
    with open(CONFIG_DIR, "w") as f:
        json.dump(data, f)


def _to_celsius(f: int) -> int:
    return round((f - 32) * 5 / 9)


def _format_temp(trend: str | None) -> str:
    if trend is None:
        return ""
    return f" ({trend})"


def _show_forecast(lat: float, lon: float, celsius: bool = False) -> None:
    pt = get_point(lat, lon)
    fc = get_forecast(pt)
    unit = "C" if celsius else "F"
    conv = _to_celsius if celsius else lambda x: x
    print(f"Forecast for {pt.city}, {pt.state}\n")
    for p in fc.periods:
        temp = conv(p.temperature)
        pop = f"  PoP: {p.probability_of_precipitation:.0f}%" if p.probability_of_precipitation is not None else ""
        print(f"{p.name}: {temp}\u00b0{unit}{_format_temp(p.temperature_trend)}{pop}")
        print(f"  {p.short_forecast}\n")


def _show_summary(lat: float, lon: float, celsius: bool = False) -> None:
    pt = get_point(lat, lon)
    fc = get_forecast(pt)
    unit = "C" if celsius else "F"
    conv = _to_celsius if celsius else lambda x: x
    print(f"Forecast for {pt.city}, {pt.state}\n")
    for d in summarize_forecast(fc):
        high = f"{conv(d.high)}\u00b0{unit}" if d.high is not None else ""
        low = f"/{conv(d.low)}\u00b0{unit}" if d.low is not None else ""
        pop = f"  PoP: {d.pop:.0f}%" if d.pop is not None else ""
        print(f"{d.symbol} {d.day_name}: {high}{low}  {d.conditions}{pop}")


_US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico", "GU": "Guam",
    "VI": "U.S. Virgin Islands", "AS": "American Samoa", "MP": "Northern Mariana Islands",
}


def _state_name(code: str) -> str:
    return _US_STATES.get(code.upper(), code) if code else code


def _spoken_clean(text: str) -> str:
    for ch in ("*", "\n", "\r", "\t", ":", ";"):
        text = text.replace(ch, " ")
    return " ".join(text.split())


def _show_spoken_summary(lat: float, lon: float, celsius: bool = False) -> None:
    pt = get_point(lat, lon)
    fc = get_forecast(pt)
    conv = _to_celsius if celsius else lambda x: x
    print(f"Forecast for {pt.city}, {_state_name(pt.state)}.")
    for d in summarize_forecast(fc):
        parts = []
        if d.high is not None:
            parts.append(f"high of {conv(d.high)}")
        if d.low is not None:
            parts.append(f"low of {conv(d.low)}")
        if d.pop is not None:
            parts.append(f"{d.pop:.0f} percent chance of precipitation")
        if d.conditions:
            parts.append(d.conditions)
        print(f"{d.day_name}, " + ", ".join(parts) + ".")


def _show_sps(results: list) -> None:
    print("Special Weather Statement in effect\n")
    for r in results:
        a = r.alert
        if r.in_polygon:
            loc = "in polygon"
        elif a.polygon is not None:
            loc = "in county/zone, not in polygon"
        else:
            loc = "in county/zone"
        print(f"  {a.headline}")
        print(f"  Areas: {a.area_desc}")
        print(f"  Location: {loc}")
        print(f"\n  {a.description}\n")


def _show_alerts(results: list) -> None:
    if not results:
        print("No active alerts for this location.")
        return
    for r in results:
        a = r.alert
        if r.in_polygon:
            loc = "in polygon"
        elif a.polygon is not None:
            loc = "in county/zone, not in polygon"
        else:
            loc = "in county/zone"
        print(f"[{a.severity}] {a.event}")
        print(f"  {a.headline}")
        print(f"  Areas: {a.area_desc}")
        print(f"  Location: {loc}")
        print(f"\n  {a.description}\n")


def _show_sps_spoken(results: list) -> None:
    for r in results:
        a = r.alert
        print("Special Weather Statement in effect.")
        if a.headline:
            print(_spoken_clean(a.headline) + ".")


def _show_alerts_spoken(results: list) -> None:
    if not results:
        print("No active alerts for this location.")
        return
    for r in results:
        a = r.alert
        line = a.event
        if a.headline:
            line += ". " + _spoken_clean(a.headline)
        print(line + ".")


def main() -> None:
    parser = argparse.ArgumentParser(prog="nwswx", description="NWS Weather Forecast & Alerts")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lon", type=float, help="Longitude")
    parser.add_argument("--address", help='Street address, e.g. "1600 Pennsylvania Ave NW, Washington, DC"')
    parser.add_argument("--save", action="store_true", help="Save location to config")
    parser.add_argument("-c", "--celsius", action="store_true", help="Show temperatures in Celsius")
    parser.add_argument("--fahrenheit", action="store_true", help="Show temperatures in Fahrenheit")
    parser.add_argument("-f", "--forecast", action="store_true", help="Show full forecast")
    parser.add_argument("-s", "--summary", action="store_true", help="Show condensed 3-day summary")
    parser.add_argument("--spoken-summary", action="store_true", help="Show TTS-friendly spoken summary")
    parser.add_argument("-a", "--alerts", action="store_true", help="Show alerts")

    args = parser.parse_args()

    lat, lon = args.lat, args.lon

    if args.address:
        parts = [p.strip() for p in args.address.split(",")]
        if len(parts) < 3:
            print("error: --address must be in format 'street, city, state' or 'street, city, state, zip'", file=sys.stderr)
            sys.exit(1)
        street, city, state = parts[0], parts[1], parts[2]
        zipcode = parts[3] if len(parts) > 3 else ""
        try:
            result = geocode(street, city, state, zipcode)
        except GeocodeError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
        if result is None:
            print("error: address not found by Census Geocoder", file=sys.stderr)
            sys.exit(1)
        lat, lon = result.lat, result.lon

    if lat is None or lon is None:
        config = _load_config()
        lat = lat or config.get("lat")
        lon = lon or config.get("lon")

    use_celsius = _load_config().get("celsius", False)
    if args.celsius:
        use_celsius = True
    if args.fahrenheit:
        use_celsius = False

    if lat is None or lon is None:
        print("No location provided. Use --lat/--lon, --address, or save a location first.", file=sys.stderr)
        sys.exit(1)

    if args.save:
        _save_config(lat, lon, celsius=use_celsius)

    show_forecast = args.forecast
    show_summary = args.summary
    show_spoken_summary = args.spoken_summary
    show_alerts = args.alerts

    if not show_forecast and not show_summary and not show_alerts and not show_spoken_summary:
        show_forecast = True
        show_alerts = True

    if show_summary:
        show_alerts = True
        try:
            _show_summary(lat, lon, celsius=use_celsius)
        except NwsApiError as e:
            print(f"error: {e}", file=sys.stderr)

    if show_spoken_summary:
        show_alerts = True
        try:
            _show_spoken_summary(lat, lon, celsius=use_celsius)
        except NwsApiError as e:
            print(f"error: {e}", file=sys.stderr)

    if show_forecast:
        try:
            _show_forecast(lat, lon, celsius=use_celsius)
        except NwsApiError as e:
            print(f"error: {e}", file=sys.stderr)

    all_alerts = None
    try:
        all_alerts = get_relevant_alerts(lat, lon)
    except NwsApiError:
        pass

    sps = [r for r in all_alerts if r.alert.event == "Special Weather Statement"] if all_alerts else []
    other = [r for r in all_alerts if r.alert.event != "Special Weather Statement"] if all_alerts else []

    if sps:
        if show_spoken_summary:
            _show_sps_spoken(sps)
        else:
            _show_sps(sps)

    if show_alerts:
        if other:
            if show_spoken_summary:
                _show_alerts_spoken(other)
            else:
                _show_alerts(other)
        elif not sps:
            print("No active alerts for this location.")
