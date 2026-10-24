import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

pages = [
    st.Page("pages/homePage.py", title="Home", default=True),
    st.Page("pages/exploreCities.py", title="Explore"),
    st.Page("pages/recommendCities.py", title="Recommend"),
    st.Page("pages/compareCities.py", title="Compare"),
    st.Page("pages/tourismTrends.py", title="Tourism"),
    st.Page("pages/cityDetails.py", title="City details"),
]
st.navigation(pages).run()
