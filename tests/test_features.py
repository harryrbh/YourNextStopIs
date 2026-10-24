"""
test_features.py — checks the normalise_0_100() function in
src/build_features.py behaves the way the docstring promises.

Run all tests with:
    pytest
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from build_features import normalise_0_100


def test_normalise_maps_to_0_100():
    result = normalise_0_100(pd.Series([10, 20, 30]))
    assert result.min() == 0
    assert result.max() == 100


def test_normalise_invert_flips_the_order():
    s = pd.Series([10, 20, 30])
    normal = normalise_0_100(s)
    inverted = normalise_0_100(s, invert=True)
    assert normal.iloc[0] == 0 and inverted.iloc[0] == 100
    assert normal.iloc[-1] == 100 and inverted.iloc[-1] == 0


def test_normalise_handles_identical_values():
    # If every city has the same value, nobody should score higher
    # than anyone else — everyone gets a neutral 50.
    result = normalise_0_100(pd.Series([7, 7, 7]))
    assert (result == 50.0).all()


def test_clipping_stops_one_outlier_squashing_everyone():
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10_000])
    plain = normalise_0_100(s)
    robust = normalise_0_100(s, log=True, clip_percent=10)
    assert plain.iloc[:9].max() < 1          # old behaviour: nine cities all score ~0
    assert robust.iloc[:9].median() > 20     # spread out
    assert robust.min() == 0 and robust.max() == 100


def test_defaults_still_plain_min_max():
    assert list(normalise_0_100(pd.Series([10, 20, 30]))) == [0, 50, 100]
