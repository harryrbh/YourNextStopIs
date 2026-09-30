"""
select_cities.py — keeps only cities that have COMPLETE data, in the
priority order of data/cities.csv (which follows src/tourist_cities.py),
up to TARGET_CITY_COUNT (250).

A city is kept only if it has ALL of:
  * a country row with GDP per person, urban-population % and tourist arrivals
    (drives Affordability and Popularity)
  * all 12 months of temperature + rainfall              (Weather)
  * >= 1 attraction, three named attractions, a heritage count (Culture & Sights)
  * >= 1 airport with >= 1 route to another kept airport (Ease of Travel)

Anything failing is dropped with the reason printed, and the next city down
the pool takes its place — so nothing reaches the app with a null in a
tourist attribute, and the app never silently invents a "neutral 50".

Pure pandas functions, no database — see tests/test_select_cities.py.
"""
import pandas as pd

TARGET_CITY_COUNT = 250


def _blank(series: pd.Series) -> pd.Series:
    return series.isna() | (series.astype(str).str.strip() == "")


def completeness_report(cities, countries, tourism, weather, culture, airports, routes) -> pd.DataFrame:
    """One row per city, with a `problem` column ('' if the city is complete)."""
    df = cities[["name", "iso2"]].copy()
    problems = {name: [] for name in df["name"]}

    def flag(mask_bad: pd.Series, reason: str):
        for name in df.loc[mask_bad, "name"]:
            problems[name].append(reason)

    # country-level facts
    c = countries.drop_duplicates("iso2").set_index("iso2")
    t = tourism.dropna(subset=["arrivals"]).drop_duplicates("iso2").set_index("iso2") if "iso2" in tourism.columns else None
    has_country = df["iso2"].isin(c.index)
    flag(~has_country, "country not in countries.csv")
    gdp = df["iso2"].map(c["gdp_per_capita_usd"]) if "gdp_per_capita_usd" in c else pd.Series(None, index=df.index)
    urb = df["iso2"].map(c["urban_population_pct"]) if "urban_population_pct" in c else pd.Series(None, index=df.index)
    flag(has_country & gdp.isna(), "no GDP per person for country")
    flag(has_country & urb.isna(), "no urban-population % for country")
    if t is None:  # sample data keyed by country name instead of iso2
        name_to_iso = countries.drop_duplicates("iso2").set_index("name")["iso2"]
        tt = tourism.dropna(subset=["arrivals"]).copy()
        tt["iso2"] = tt["country_name"].map(name_to_iso)
        t = tt.dropna(subset=["iso2"]).drop_duplicates("iso2").set_index("iso2")
    flag(~df["iso2"].isin(t.index), "no tourist-arrival figures for country")

    # weather: 12 months, no nulls
    w = weather.dropna(subset=["temperature_c", "precipitation_mm"]).groupby("city_name")["month"].nunique()
    flag(df["name"].map(w).fillna(0) < 12, "incomplete weather data")

    # culture
    cu = culture.drop_duplicates("city_name").set_index("city_name")
    in_culture = df["name"].isin(cu.index)
    flag(~in_culture, "no culture data")
    attr_n = df["name"].map(cu["attraction_count"]).fillna(0)
    flag(in_culture & (attr_n < 1), "no tourist attractions")
    heritage = df["name"].map(cu["heritage_site_count"])
    flag(in_culture & heritage.isna(), "no heritage-site count")
    for col in ["attraction_1", "attraction_2", "attraction_3"]:
        vals = df["name"].map(cu[col])
        flag(in_culture & (attr_n >= 1) & _blank(vals), f"missing {col}")

    # ease of travel: an airport with at least one route
    ap = airports.dropna(subset=["iata_code"])
    routed = set(routes["source_iata"]) | set(routes["destination_iata"])
    ap = ap[ap["iata_code"].isin(routed)]
    flag(~df["name"].isin(set(ap["city_name"])), "no airport with flight routes nearby")

    df["problem"] = df["name"].map(lambda n: "; ".join(problems[n]))
    return df


def select_cities(cities, countries, tourism, weather, culture, airports, routes,
                  target: int = TARGET_CITY_COUNT):
    """Return (kept_city_names_in_priority_order, report_of_dropped)."""
    report = completeness_report(cities, countries, tourism, weather, culture, airports, routes)
    complete = report[report["problem"] == ""]
    kept = complete["name"].head(target).tolist()
    dropped = report[report["problem"] != ""][["name", "iso2", "problem"]]
    return kept, dropped
