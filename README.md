# nwswx

Get weather forecasts and active alerts from the US National Weather Service.

## Features

- **Forecast** — 7-day detailed or 3-day condensed summary with weather symbols
- **Alerts** — active watches, warnings, and advisories for your location (polygon + zone/county)
- **Geocoding** — look up coordinates by street address via the Census Geocoder
- **Location persistence** — saved to `~/.config/nwswx.json`

## Install

```bash
pip install nwswx
```

Or with Poetry:

```bash
poetry install
```

## Usage

```bash
# By coordinates
nwswx --lat 38.9072 --lon -77.0369

# By street address
nwswx --address "1600 Pennsylvania Ave NW, Washington, DC"

# Save a location so you can run without flags
nwswx --lat 38.9072 --lon -77.0369 --save
nwswx

# Flags
nwswx -s          # condensed 3-day summary
nwswx -f          # full forecast
nwswx -a          # active alerts only
nwswx -sa         # summary + alerts
```

## API

```python
from nwswx.client import get_point
pt = get_point(38.9072, -77.0369)
# pt.grid_id, pt.forecast_url, pt.county_id, pt.city, pt.state ...

from nwswx.forecast import get_forecast, summarize_forecast
fc = get_forecast(pt)
for p in fc.periods:
    print(p.name, p.temperature, p.short_forecast)

for d in summarize_forecast(fc):
    print(d.symbol, d.day_name, d.high, d.low, d.pop)

from nwswx.alerts import get_relevant_alerts
for a in get_relevant_alerts(38.9072, -77.0369):
    print(a.severity, a.event, a.headline)

from nwswx.geocode import geocode
r = geocode("1600 Pennsylvania Ave NW", "Washington", "DC")
print(r.lat, r.lon)
```

## License

MIT
