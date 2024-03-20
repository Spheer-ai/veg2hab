import geopandas as gpd
import pytest

from veg2hab.vegkartering import ingest_vegtype_column


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
    post = ingest_vegtype_column(
        gdf = gdf, 
        ElmID_col="ElmID",
        sbb_of_vvn="beide",
        sbb_cols=["SBB1"],
        vnn_cols=None,
        perc_col=["perc1"],
    )



def test_single_VvN():
    pass


def test_both_SBB_and_VvN():
    pass


def test_multiple_SBB():
    pass


def test_multiple_SBB_and_VvN():
    pass


def test_SBB_with_some_VvN():
    pass


def test_xor_SBB_and_VvN():
    pass


def test_none_SBB():
    pass


def test_none_SBB_and_VvN():
    pass


def test_mismatch_num_vegtype_columns():
    pass


def test_columns_dont_exist():
    pass


