import argparse
import json
import os
import sys

from nwswx.alerts import get_relevant_alerts
from nwswx.client import get_point
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


def _show_alerts(lat: float, lon: float) -> None:
    alerts = get_relevant_alerts(lat, lon)
    if not alerts:
        print("No active alerts for this location.")
        return
    for a in alerts:
        print(f"[{a.severity}] {a.event}")
        print(f"  {a.headline}")
        print(f"  Areas: {a.area_desc}\n")


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
    show_alerts = args.alerts

    if not show_forecast and not show_summary and not show_alerts:
        show_forecast = True
        show_alerts = True

    if show_summary:
        _show_summary(lat, lon, celsius=use_celsius)

    if show_forecast:
        _show_forecast(lat, lon, celsius=use_celsius)

    if show_alerts:
        _show_alerts(lat, lon)
