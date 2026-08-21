"""
app.py — the Streamlit app's home page.

Run it with:
    streamlit run app.py

Streamlit automatically turns every file in pages/ into an extra page
in the sidebar — that's the only "magic" in this project. Everything
else is plain Python.
"""
import plotly.express as px
import streamlit as st

from data_access import load_cities

st.set_page_config(page_title="City Break Recommender", page_icon="🌍", layout="wide")


def main():
    st.title("🌍 City Break Recommender")
    st.caption("Find your next short break using real airport, weather and cultural data.")

    try:
        cities = load_cities()
    except Exception as e:
        st.error(
            "Couldn't connect to the database. Is PostgreSQL running, and have you "
            f"run `python src/load_data.py` and `python src/build_features.py` yet?\n\nError: {e}"
        )
        st.stop()

    if cities.empty:
        st.warning("No data found. Run the setup steps in README.md first.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Cities", len(cities))
    col2.metric("Countries", cities["country_name"].nunique())
    col3.metric("Average score", f"{cities['overall_score'].mean():.0f}/100")

    st.subheader("All cities, by overall score")
    fig = px.scatter_geo(
        cities, lat="latitude", lon="longitude", hover_name="city_name",
        color="overall_score", size="tourist_arrivals",
        color_continuous_scale="Viridis", projection="natural earth",
    )
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 destinations right now")
    top10 = cities.sort_values("overall_score", ascending=False).head(10)
    st.dataframe(
        top10[["city_name", "country_name", "overall_score", "weather_score", "cost_score"]],
        use_container_width=True, hide_index=True,
    )

    st.info("Use the sidebar to explore cities, get a personal recommendation, or compare a few side by side.")


if __name__ == "__main__":
    main()
