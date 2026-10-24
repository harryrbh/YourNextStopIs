"""Checks the normalise_0_100() function in src/buildCityFeatures.py behaves the way the docstring promises."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from buildCityFeatures import normaliseToScore


def testNormaliseMapsTo0100():
    result = normaliseToScore(pd.Series([10, 20, 30]))
    assert result.min() == 0
    assert result.max() == 100


def testNormaliseInvertFlipsTheOrder():
    series = pd.Series([10, 20, 30])
    normal = normaliseToScore(series)
    inverted = normaliseToScore(series, invert=True)
    assert normal.iloc[0] == 0 and inverted.iloc[0] == 100
    assert normal.iloc[-1] == 100 and inverted.iloc[-1] == 0


def testNormaliseHandlesIdenticalValues():
    # If every city has the same value, nobody should score higher than anyone else
    result = normaliseToScore(pd.Series([7, 7, 7]))
    assert (result == 50.0).all()


def testClippingStopsOneOutlierSquashingEveryone():
    series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10_000])
    plain = normaliseToScore(series)
    robust = normaliseToScore(series, useLogScale=True, clipPercent=10)
    assert plain.iloc[:9].max() < 1  # Old behaviour: nine cities all score ~0
    assert robust.iloc[:9].median() > 20  # Spread out
    assert robust.min() == 0 and robust.max() == 100


def testDefaultsStillPlainMinimumMaximum():
    assert list(normaliseToScore(pd.Series([10, 20, 30]))) == [0, 50, 100]
