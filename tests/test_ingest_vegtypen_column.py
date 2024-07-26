from typing import List, Optional

import geopandas as gpd
import pandas as pd
import pytest

from veg2hab.vegkartering import VegTypeInfo, ingest_vegtype


@pytest.fixture
def gdf():
    return gpd.GeoDataFrame(
        {
            "ElmID": [1, 2, 3],
            "SBB1": ["25a1", "25a2", "25a3"],
            "SBB2": ["26a1", "26a2", "26a3"],
            "VvN1": ["25aa1", "25aa2", "25aa3"],
            "VvN2": ["26aa1", "26aa2", "26aa3"],
            "perc1": [60, 50, 70],
            "perc2": [40, 50, 30],
        }
    )


def test_single_SBB(gdf):
    post = ingest_vegtype(
        gdf=gdf,
        SBB_cols=["SBB1"],
        VvN_cols=[],
        perc_cols=["perc1"],
    )
    expected = pd.Series(
        [
            [VegTypeInfo.from_str_vegtypes(60, SBB_strings=["25a1"])],
            [VegTypeInfo.from_str_vegtypes(50, SBB_strings=["25a2"])],
            [VegTypeInfo.from_str_vegtypes(70, SBB_strings=["25a3"])],
        ],
        name="vegtype",
    )
    assert post.equals(expected)


def test_single_VvN(gdf):
    post = ingest_vegtype(
        gdf=gdf,
        SBB_cols=[],
        VvN_cols=["VvN1"],
        perc_cols=["perc1"],
    )
    expected = pd.Series(
        [
            [VegTypeInfo.from_str_vegtypes(60, VvN_strings=["25aa1"])],
            [VegTypeInfo.from_str_vegtypes(50, VvN_strings=["25aa2"])],
            [VegTypeInfo.from_str_vegtypes(70, VvN_strings=["25aa3"])],
        ],
        name="vegtype",
    )
    assert post.equals(expected)


def test_both_SBB_and_VvN(gdf):
    post = ingest_vegtype(
        gdf=gdf,
        SBB_cols=["SBB1"],
        VvN_cols=["VvN1"],
        perc_cols=["perc1"],
    )
    expected = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(
                    60, SBB_strings=["25a1"], VvN_strings=["25aa1"]
                )
            ],
            [
                VegTypeInfo.from_str_vegtypes(
                    50, SBB_strings=["25a2"], VvN_strings=["25aa2"]
                )
            ],
            [
                VegTypeInfo.from_str_vegtypes(
                    70, SBB_strings=["25a3"], VvN_strings=["25aa3"]
                )
            ],
        ],
        name="vegtype",
    )
    assert post.equals(expected)


def test_multiple_SBB(gdf):
    post = ingest_vegtype(
        gdf=gdf,
        SBB_cols=["SBB1", "SBB2"],
        VvN_cols=[],
        perc_cols=["perc1", "perc2"],
    )
    expected = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(60, SBB_strings=["25a1"]),
                VegTypeInfo.from_str_vegtypes(40, SBB_strings=["26a1"]),
            ],
            [
                VegTypeInfo.from_str_vegtypes(50, SBB_strings=["25a2"]),
                VegTypeInfo.from_str_vegtypes(50, SBB_strings=["26a2"]),
            ],
            [
                VegTypeInfo.from_str_vegtypes(70, SBB_strings=["25a3"]),
                VegTypeInfo.from_str_vegtypes(30, SBB_strings=["26a3"]),
            ],
        ],
        name="vegtype",
    )
    assert post.equals(expected)


def test_multiple_SBB_and_VvN(gdf):
    post = ingest_vegtype(
        gdf=gdf,
        SBB_cols=["SBB1", "SBB2"],
        VvN_cols=["VvN1", "VvN2"],
        perc_cols=["perc1", "perc2"],
    )
    expected = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(
                    60, SBB_strings=["25a1"], VvN_strings=["25aa1"]
                ),
                VegTypeInfo.from_str_vegtypes(
                    40, SBB_strings=["26a1"], VvN_strings=["26aa1"]
                ),
            ],
            [
                VegTypeInfo.from_str_vegtypes(
                    50, SBB_strings=["25a2"], VvN_strings=["25aa2"]
                ),
                VegTypeInfo.from_str_vegtypes(
                    50, SBB_strings=["26a2"], VvN_strings=["26aa2"]
                ),
            ],
            [
                VegTypeInfo.from_str_vegtypes(
                    70, SBB_strings=["25a3"], VvN_strings=["25aa3"]
                ),
                VegTypeInfo.from_str_vegtypes(
                    30, SBB_strings=["26a3"], VvN_strings=["26aa3"]
                ),
            ],
        ],
        name="vegtype",
    )
    assert post.equals(expected)


def test_SBB_with_some_VvN(gdf):
    gdf["VvN1"] = [None, "25aa2", "25aa3"]
    gdf["SBB2"] = ["26a1", None, "26a3"]
    post = ingest_vegtype(
        gdf=gdf,
        SBB_cols=["SBB1", "SBB2"],
        VvN_cols=["VvN1", "VvN2"],
        perc_cols=["perc1", "perc2"],
    )
    expected = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(60, SBB_strings=["25a1"]),
                VegTypeInfo.from_str_vegtypes(
                    40, SBB_strings=["26a1"], VvN_strings=["26aa1"]
                ),
            ],
            [
                VegTypeInfo.from_str_vegtypes(
                    50, SBB_strings=["25a2"], VvN_strings=["25aa2"]
                ),
                VegTypeInfo.from_str_vegtypes(50, VvN_strings=["26aa2"]),
            ],
            [
                VegTypeInfo.from_str_vegtypes(
                    70, SBB_strings=["25a3"], VvN_strings=["25aa3"]
                ),
                VegTypeInfo.from_str_vegtypes(
                    30, SBB_strings=["26a3"], VvN_strings=["26aa3"]
                ),
            ],
        ],
        name="vegtype",
    )
    assert post.equals(expected)


def test_none_SBB(gdf):
    gdf["VvN1"] = ["25aa1", None, None]
    gdf["SBB1"] = ["25a1", None, None]
    gdf["VvN2"] = [None] * 3
    gdf["SBB2"] = [None] * 3
    post = ingest_vegtype(
        gdf=gdf,
        SBB_cols=["SBB1", "SBB2"],
        VvN_cols=["VvN1", "VvN2"],
        perc_cols=["perc1", "perc2"],
    )
    expected = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(
                    60, SBB_strings=["25a1"], VvN_strings=["25aa1"]
                ),
            ],
            [VegTypeInfo(percentage=100, SBB=[], VvN=[])],
            [VegTypeInfo(percentage=100, SBB=[], VvN=[])],
        ],
        name="vegtype",
    )
    assert post.equals(expected)


def test_mixed_complex_and_non_complex(gdf):
    gdf.loc[0, "SBB2"] = None
    gdf.loc[0, "VvN2"] = None
    gdf.loc[0, "perc2"] = None
    gdf.loc[0, "perc1"] = 100

    gdf.loc[1, "SBB2"] = None
    gdf.loc[1, "VvN2"] = None
    gdf.loc[1, "perc2"] = 0  # both 0 and None should work
    gdf.loc[1, "perc1"] = 100

    post = ingest_vegtype(
        gdf=gdf,
        SBB_cols=["SBB1", "SBB2"],
        VvN_cols=["VvN1", "VvN2"],
        perc_cols=["perc1", "perc2"],
    )

    expected = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(
                    100, SBB_strings=["25a1"], VvN_strings=["25aa1"]
                ),
            ],
            [
                VegTypeInfo.from_str_vegtypes(
                    100, SBB_strings=["25a2"], VvN_strings=["25aa2"]
                ),
            ],
            [
                VegTypeInfo.from_str_vegtypes(
                    70, SBB_strings=["25a3"], VvN_strings=["25aa3"]
                ),
                VegTypeInfo.from_str_vegtypes(
                    30, SBB_strings=["26a3"], VvN_strings=["26aa3"]
                ),
            ],
        ],
        name="vegtype",
    )
    assert expected.equals(post)


def test_mismatch_num_columns(gdf):
    with pytest.raises(ValueError):
        ingest_vegtype(
            gdf=gdf,
            SBB_cols=["SBB1", "SBB2"],
            VvN_cols=["VvN1"],
            perc_cols=["perc1", "perc2"],
        )

    with pytest.raises(ValueError):
        ingest_vegtype(
            gdf=gdf,
            SBB_cols=["SBB1"],
            VvN_cols=None,
            perc_cols=["perc1", "perc2"],
        )


def test_columns_dont_exist(gdf):
    with pytest.raises(KeyError):
        ingest_vegtype(
            gdf=gdf,
            SBB_cols=["SBB1", "SBB3"],
            VvN_cols=[],
            perc_cols=["perc1", "perc2"],
        )
