"""Checks the recommender returns sensible output."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from recommendSimilarCities import featureColumns, loadCitiesWithScores, recommend

try:
    _cities = loadCitiesWithScores()
    dbReady = not _cities.empty
except Exception:
    dbReady = False

pytestmark = pytest.mark.skipif(not dbReady, reason="database not running or not loaded yet")


def testRecommendReturnsRequestedNumberOfCities():
    result = recommend({"weather_score": 80}, topN=5)
    assert len(result) == 5


def testRecommendSimilarityBetweenMinus1And1():
    result = recommend({"cost_score": 90}, topN=5)
    assert (result["similarity"] >= -1.0001).all()
    assert (result["similarity"] <= 1.0001).all()


def testRecommendSortedBestMatchFirst():
    result = recommend({}, topN=8)
    similarities = list(result["similarity"])
    assert similarities == sorted(similarities, reverse=True)


def testAllFeatureColumnsPresent():
    result = recommend({}, topN=3)
    for featureName in featureColumns:
        assert featureName in result.columns
