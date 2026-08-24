"""
app.py — the app's home page.

Run it with:
    streamlit run app.py

Streamlit automatically turns every file in pages/ into an extra page
in the sidebar — that's the only "magic" in this project. Everything
else is plain Python.
"""
import matplotlib.pyplot as plt
import streamlit as st

from data_access import load_cities
from labels import friendly
from theme import CMAP, GREEN

st.set_page_config(page_title="City Breaks", page_icon="🧭", layout="wide")


def main():
    st.title("🧭 City Breaks")
    st.caption("Find your next short break using real airport, weather and travel data.")

    try:
        cities = load_cities()
    except Exception as e:
        st.error(
            "Couldn't open the database. Have you run `python src/db.py`, "
            f"`python src/load_data.py` and `python src/build_features.py` yet?\n\nDetails: {e}"
        )
        st.stop()

    if cities.empty:
        st.warning("No data found. Run the setup steps in README.md first.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Cities", len(cities))
    col2.metric("Countries", cities["country_name"].nunique())
    col3.metric("Average score", f"{cities['overall_score'].mean():.0f}/100")

    st.subheader("Where every city is")
    fig, ax = plt.subplots(figsize=(10, 5))
    scatter = ax.scatter(
        cities["longitude"], cities["latitude"],
        c=cities["overall_score"], cmap=CMAP, s=60, edgecolors="white", linewidths=0.5,
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_facecolor("#F7FAFC")
    fig.colorbar(scatter, ax=ax, label="Overall score")
    fig.tight_layout()
    st.pyplot(fig)

    st.subheader("Top 10 right now")
    top10 = cities.sort_values("overall_score", ascending=False).head(10)

    fig2, ax2 = plt.subplots(figsize=(8, 4.5))
    ax2.barh(top10["city_name"][::-1], top10["overall_score"][::-1], color=GREEN)
    ax2.set_xlabel("Overall score")
    ax2.set_xlim(0, 100)
    fig2.tight_layout()
    st.pyplot(fig2)

    st.dataframe(
        friendly(top10[["city_name", "country_name", "overall_score", "weather_score", "cost_score"]]),
        use_container_width=True, hide_index=True,
    )

    st.info("Use the sidebar to explore, get a recommendation, or compare cities.")


if __name__ == "__main__":
    main()
