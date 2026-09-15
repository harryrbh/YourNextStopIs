"""
components.py — the reusable "city card" used on the Explore and
Recommend pages, so a city looks the same wherever it appears: photo,
flag, key stats, top attraction, price tier, and (in an expander)
direct flights.
"""
import pandas as pd
import streamlit as st

from images import get_city_image_url
from labels import flag_image_html
from theme import score_badge_html


def render_city_card(
    row: pd.Series,
    direct_flights: list[str] | None = None,
    badge_value: float | None = None,
    badge_suffix: str = "/100",
):
    """row needs: city_name, country_name, iso2, overall_score,
    avg_temperature_c, attraction_1, category, price_tier,
    airport_count. `direct_flights` is an optional list of city names
    with a direct route from this city (see pages for how it's built).
    By default the top-right badge shows the overall score; pass
    `badge_value`/`badge_suffix` to show something else instead (e.g.
    Recommend shows a match percentage).
    """
    with st.container(border=True):
        image_url = get_city_image_url(row["city_name"], row.get("country_name", ""))
        if image_url:
            st.image(image_url, use_container_width=True)

        top = st.columns([4, 1])
        flag = flag_image_html(row.get("iso2", ""))
        top[0].markdown(
            f'<div class="city-card-title">{flag} {row["city_name"]}</div>'
            f'<div class="city-card-subtitle">{row["country_name"]}</div>',
            unsafe_allow_html=True,
        )
        value = badge_value if badge_value is not None else row["overall_score"]
        top[1].markdown(
            f'<div style="text-align:right; padding-top:6px;">'
            f'{score_badge_html(value, badge_suffix)}</div>',
            unsafe_allow_html=True,
        )

        caption_bits = [b for b in [row.get("category"), row.get("price_tier")] if b]
        if caption_bits:
            st.caption(" · ".join(caption_bits))

        chips = []
        if pd.notna(row.get("avg_temperature_c")):
            chips.append(f"{row['avg_temperature_c']:.0f}°C avg")
        if row.get("attraction_1"):
            chips.append(f"Top sight: {row['attraction_1']}")
        if pd.notna(row.get("airport_count")):
            chips.append(f"{int(row['airport_count'])} airports")
        if chips:
            st.markdown(
                "".join(f'<span class="stat-chip">{c}</span>' for c in chips),
                unsafe_allow_html=True,
            )

        if direct_flights:
            with st.expander(f"Direct flights ({len(direct_flights)})"):
                st.write(", ".join(direct_flights) if direct_flights else "None tracked")
