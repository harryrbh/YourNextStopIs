import pandas as pd

targetCityCount = 250


def _blank(series: pd.Series) -> pd.Series:
    return series.isna() | (series.astype(str).str.strip() == "")


def completenessReport(cities, countries, tourism, weather, culture, airports, routes) -> pd.DataFrame:
    """One row per city, with a `problem` column ('' if the city is complete)."""
    cityTable = cities[["name", "iso2"]].copy()
    problems = {name: [] for name in cityTable["name"]}

    def flag(maskBad: pd.Series, reason: str):
        for name in cityTable.loc[maskBad, "name"]:
            problems[name].append(reason)

    # Country-level facts
    countryTable = countries.drop_duplicates("iso2").set_index("iso2")
    arrivalsByCountry = tourism.dropna(subset=["arrivals"]).drop_duplicates("iso2").set_index("iso2") if "iso2" in tourism.columns else None
    hasCountry = cityTable["iso2"].isin(countryTable.index)
    flag(~hasCountry, "country not in countries.csv")
    gdpPerCapita = cityTable["iso2"].map(countryTable["gdp_per_capita_usd"]) if "gdp_per_capita_usd" in countryTable else pd.Series(None, index=cityTable.index)
    urbanShare = cityTable["iso2"].map(countryTable["urban_population_pct"]) if "urban_population_pct" in countryTable else pd.Series(None, index=cityTable.index)
    flag(hasCountry & gdpPerCapita.isna(), "no GDP per person for country")
    flag(hasCountry & urbanShare.isna(), "no urban-population % for country")
    if arrivalsByCountry is None:  # Sample data keyed by country name instead of iso2
        nameToIso = countries.drop_duplicates("iso2").set_index("name")["iso2"]
        arrivalsTable = tourism.dropna(subset=["arrivals"]).copy()
        arrivalsTable["iso2"] = arrivalsTable["country_name"].map(nameToIso)
        arrivalsByCountry = arrivalsTable.dropna(subset=["iso2"]).drop_duplicates("iso2").set_index("iso2")
    flag(~cityTable["iso2"].isin(arrivalsByCountry.index), "no tourist-arrival figures for country")

    # Weather: 12 months, no nulls
    weatherMonths = weather.dropna(subset=["temperature_c", "precipitation_mm"]).groupby("city_name")["month"].nunique()
    flag(cityTable["name"].map(weatherMonths).fillna(0) < 12, "incomplete weather data")

    cultureByCity = culture.drop_duplicates("city_name").set_index("city_name")
    inCulture = cityTable["name"].isin(cultureByCity.index)
    flag(~inCulture, "no culture data")
    attractionN = cityTable["name"].map(cultureByCity["attraction_count"]).fillna(0)
    flag(inCulture & (attractionN < 1), "no tourist attractions")
    heritage = cityTable["name"].map(cultureByCity["heritage_site_count"])
    flag(inCulture & heritage.isna(), "no heritage-site count")
    for attractionColumn in ["attraction_1", "attraction_2", "attraction_3"]:
        vals = cityTable["name"].map(cultureByCity[attractionColumn])
        flag(inCulture & (attractionN >= 1) & _blank(vals), f"missing {attractionColumn}")

    # Ease of travel: an airport with at least one route
    routedAirports = airports.dropna(subset=["iata_code"])
    routed = set(routes["source_iata"]) | set(routes["destination_iata"])
    routedAirports = routedAirports[routedAirports["iata_code"].isin(routed)]
    flag(~cityTable["name"].isin(set(routedAirports["city_name"])), "no airport with flight routes nearby")

    cityTable["problem"] = cityTable["name"].map(lambda cityName: "; ".join(problems[cityName]))
    return cityTable


def selectCities(cities, countries, tourism, weather, culture, airports, routes,
                  target: int = targetCityCount):
    """Return (kept_city_names_in_priority_order, report_of_dropped)."""
    report = completenessReport(cities, countries, tourism, weather, culture, airports, routes)
    complete = report[report["problem"] == ""]
    kept = complete["name"].head(target).tolist()
    dropped = report[report["problem"] != ""][["name", "iso2", "problem"]]
    return kept, dropped
