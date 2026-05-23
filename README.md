# nwswx

CLI tool and Python library for weather forecasts and active alerts from the US National Weather Service.

## Features

- **Forecast** — 7-day detailed or 3-day condensed summary with weather symbols
- **Alerts** — active watches, warnings, and advisories by polygon, zone, and county
- **Geocoding** — resolve street addresses to coordinates via the Census Geocoder
- **Location persistence** — save a default location to `~/.config/nwswx.json`
- **Graceful error handling** — network errors and NWS API failures display clear messages instead of tracebacks
- **Timeouts** — all HTTP requests timeout after 15 seconds

## Requirements

- Python >= 3.13

## Install

```bash
pip install nwswx
```

Or with pipx:

```bash
pipx install nwswx
```

Or from source:

```bash
git clone https://github.com/yourusername/nwswx
cd nwswx
pip install .
```

## CLI Usage

```bash
# By coordinates
nwswx --lat 38.9072 --lon -77.0369

# By street address
nwswx --address "1600 Pennsylvania Ave NW, Washington, DC"

# Save a default location
nwswx --lat 38.9072 --lon -77.0369 --save
nwswx                     # uses saved location

# Display options
nwswx -s                  # 3-day summary
nwswx -f                  # full 7-day forecast
nwswx -a                  # active alerts only
nwswx -sa                 # summary + alerts

# Temperature units
nwswx -c                  # Celsius
nwswx --fahrenheit        # Fahrenheit (default)
```

### Output example

```
Forecast for Washington, DC

⛈️ This Afternoon: 56°F/54°F  Showers And Thunderstorms  PoP: 99%
🌧️ Sunday: 74°F/61°F  Rain Showers  PoP: 90%
⛈️ Memorial Day: 80°F/63°F  Chance Showers And Thunderstorms  PoP: 57%
No active alerts for this location.
```

## Python API

```python
from nwswx.client import get_point
from nwswx.forecast import get_forecast, summarize_forecast
from nwswx.alerts import get_relevant_alerts
from nwswx.geocode import geocode
from nwswx.exceptions import NwsApiError
```

### Geocoding

```python
result = geocode("1600 Pennsylvania Ave NW", "Washington", "DC")
print(result.lat, result.lon)
```

### Point lookup

```python
pt = get_point(38.9072, -77.0369)
print(pt.city, pt.state)           # Washington, DC
print(pt.grid_id, pt.grid_x, pt.grid_y)
print(pt.forecast_url)
print(pt.county_id)                # DCC001
print(pt.forecast_zone_id)         # DCZ001
print(pt.fire_weather_zone_id)
```

### Forecast

```python
fc = get_forecast(pt)
for p in fc.periods:
    print(p.name, p.temperature, p.short_forecast)

for d in summarize_forecast(fc, days=3):
    print(d.symbol, d.day_name, d.high, d.low, d.pop)
```

### Alerts

```python
for a in get_relevant_alerts(38.9072, -77.0369):
    print(f"[{a.alert.severity}] {a.alert.event}")
    print(f"  {a.alert.headline}")
    print(f"  In polygon: {a.in_polygon}")
```

### Error handling

All HTTP request functions raise `NwsApiError` on failure — catch it for graceful degradation:

```python
try:
    pt = get_point(38.9072, -77.0369)
except NwsApiError as e:
    print(f"Weather data unavailable: {e}")
```

## Configuration

Saved to `~/.config/nwswx.json`:

```json
{"lat": 38.9072, "lon": -77.0369, "celsius": true}
```

## License

MIT
