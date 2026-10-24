import pandas as pd
import streamlit as st

from cityImages import getCityImageUrl
from displayLabels import flagImageHtml
from themeStyles import scoreBadgeHtml


def renderCityCard(
    row: pd.Series,
    directFlights: list[str] | None = None,
    badgeValue: float | None = None,
    badgeSuffix: str = "/100",
):
    with st.container(border=True):
        imageUrl = getCityImageUrl(row["city_name"], row.get("country_name", ""))
        if imageUrl:
            st.image(imageUrl, width="stretch")

        headerColumns = st.columns([4, 1])
        flag = flagImageHtml(row.get("iso2", ""))
        headerColumns[0].markdown(
            f'<div class="city-card-title">{flag} {row["city_name"]}</div>'
            f'<div class="city-card-subtitle">{row["country_name"]}</div>',
            unsafe_allow_html=True,
        )
        badgeNumber = badgeValue if badgeValue is not None else row["overall_score"]
        headerColumns[1].markdown(
            f'<div style="text-align:right; padding-top:6px;">'
            f'{scoreBadgeHtml(badgeNumber, badgeSuffix)}</div>',
            unsafe_allow_html=True,
        )

        captionBits = [str(captionPart) for captionPart in [row.get("category"), row.get("price_tier")] if pd.notna(captionPart)]
        if captionBits:
            st.caption(" · ".join(captionBits))

        chips = []
        if pd.notna(row.get("avg_temperature_c")):
            chips.append(f"{row['avg_temperature_c']:.0f}°C avg")
        if pd.notna(row.get("attraction_1")):
            chips.append(f"Top sight: {row['attraction_1']}")
        if pd.notna(row.get("airport_count")):
            chips.append(f"{int(row['airport_count'])} airports")
        if chips:
            st.markdown(
                "".join(f'<span class="stat-chip">{chipText}</span>' for chipText in chips),
                unsafe_allow_html=True,
            )

        if directFlights:
            with st.expander(f"Direct flights ({len(directFlights)})"):
                st.write(", ".join(directFlights) if directFlights else "None")
