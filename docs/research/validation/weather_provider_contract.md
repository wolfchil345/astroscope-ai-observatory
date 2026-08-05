# Weather Interval Provider-Contract Evidence

Mission 31 records offline, first-party Open-Meteo provider-contract evidence
for AstroScope weather sample timestamps. It does not validate weather-model
accuracy, forecast skill, or observed meteorological conditions.

## Documented provider contract

The [Forecast API](https://open-meteo.com/en/docs) documents `timezone`,
`start_date`, `end_date`, hourly data, and `timeformat=unixtime`; Unix values
are specified as GMT+0. The [Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api)
documents that it uses the Forecast API parameters and response format.

## Archived response evidence

The committed fixture was retrieved on 2026-08-05 from the Historical Forecast
API with `hourly=temperature_2m`. It contains normalized timestamp and metadata
evidence for Tokyo, New York spring/fall transitions, London fall-back, and
Lord Howe spring/fall transitions. Named-zone ISO timestamps were offset-free;
Unix values reconstructed through Python `ZoneInfo` preserve physical ordering,
offsets, and folds for returned samples.

The fixture also records that named-zone calendar requests did not reliably
form a complete transition-day physical envelope. Production therefore uses a
GMT Unix request bounded by resolved UTC endpoint dates, then performs closed
sample filtering in UTC.

## AstroScope regression correction

Weather records are mixed-variable forecast records keyed by one provider-valid
timestamp. Most selected variables are instantaneous; precipitation-related
variables have preceding-hour support. AstroScope selects records in the closed
envelope `start_utc <= sample_utc <= end_utc`; it does not reinterpret provider
bucket support or calculate forecast accuracy.

The offline runner verifies the fixture integrity and scenario categories:

```text
python -m validation.weather_provider \
  --manifest validation/manifests/weather_provider_contract_v1.json \
  --output /tmp/weather-provider-run.json
```
