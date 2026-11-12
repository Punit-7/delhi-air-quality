# Project brief: what drives Delhi's November smog?

## The question
How much of Delhi's hourly PM2.5 in October and November 2026 moves with
weather, farm fires upwind, and the Diwali night, and how much is left over
for year-round local sources?

## Who would use the answer
A city air-quality team deciding where to spend effort: emergency curbs on
bad-weather days, pressure on stubble burning, or firecracker enforcement.

## What "done" looks like
1. A pipeline that refreshes every hour without anyone touching it.
2. A Grafana dashboard that answers "how bad is it right now, and where?"
3. A short written finding with numbers, limits, and one recommendation.

## Metrics
| Metric | Definition | Source table |
|---|---|---|
| City PM2.5 | Mean of station hourly PM2.5, only when 5+ stations report | marts.fct_city_hourly |
| Station daily PM2.5 | 24-hour mean per station, only with 16+ hours of data | marts.fct_station_daily |
| AQI category | CPCB sub-index bands applied to the 24-hour PM2.5 mean | marts.fct_station_daily |
| Fire count | Satellite detections per day over Punjab and Haryana | marts.fct_fires_daily |

## Data sources
| Source | What | Refresh | Access |
|---|---|---|---|
| OpenAQ v3 | Hourly PM2.5, PM10, NO2 from Delhi monitors | Hourly | Free API key |
| Open-Meteo | Hourly wind, temperature, humidity, boundary layer height | Hourly | No key |
| NASA FIRMS | Fire detections from the VIIRS satellite sensor | Several passes a day | Free MAP_KEY |

## Out of scope
- Forecasting tomorrow's AQI.
- Source apportionment in the scientific sense. This project measures
  association, not cause.
- The official AQI, which also needs other pollutants. We report the PM2.5
  sub-index only and label it that way.

## Known risks
- Stations go offline and the feed has gaps, most often on the worst days.
- Many monitors stop reading near 1,000 µg/m³, so peak hours are understated.
- About six weeks of data is a short window for a statistical model.