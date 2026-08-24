"""
test_recommend.py — checks the recommender returns sensible output.

These tests need a populated database (same as the app itself), so
they skip automatically if one isn't available — you won't see a
confusing failure just because you haven't run the setup steps yet.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from recommend import FEATURES, load_cities_with_scores, recommend

try:
    _cities = load_cities_with_scores()
    DB_READY = not _cities.empty
except Exception:
    DB_READY = False

pytestmark = pytest.mark.skipif(not DB_READY, reason="database not running or not loaded yet")


def test_recommend_returns_requested_number_of_cities():
    result = recommend({"weather_score": 80}, top_n=5)
    assert len(result) == 5


def test_recommend_similarity_between_minus1_and_1():
    result = recommend({"cost_score": 90}, top_n=5)
    assert (result["similarity"] >= -1.0001).all()
    assert (result["similarity"] <= 1.0001).all()


def test_recommend_sorted_best_match_first():
    result = recommend({}, top_n=8)
    similarities = list(result["similarity"])
    assert similarities == sorted(similarities, reverse=True)


def test_all_feature_columns_present():
    result = recommend({}, top_n=3)
    for col in FEATURES:
        assert col in result.columns
