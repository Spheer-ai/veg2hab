import geopandas as gpd
import pandas as pd
from pytest import fixture
from shapely.geometry import Polygon

from veg2hab.validation import (
    bereken_percentage_confusion_matrix,
    bereken_percentage_correct,
    bereken_volledige_conf_matrix,
    parse_habitat_percentages,
    spatial_join,
    voeg_correctheid_toe_aan_df,
)


@fixture
def gdf():
    return gpd.GeoDataFrame(
        # in principle this is invalid data.
        # They should be ordered by percentage (and habtype 0 is alway first)
        data={
            "Habtype1": ["H123", "H123", "H345", None],
            "Perc1": [80, 20, 40, 0],
            "Habtype2": ["H234", "H234", "H123", None],
            "Perc2": [20, 80, 40, 0],
            "Habtype3": [None, None, "H234", "H456"],
            "Perc3": [0, 0, 20, 100],
        },
        geometry=gpd.points_from_xy([0, 1, 2, 3], [0, 1, 2, 3]),
    )


@fixture
def gdf_single_square_1():
    return gpd.GeoDataFrame(
        data={
            "Habtype1": ["H123"],
            "Perc1": [100],
        },
        geometry=[Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])],
    )


@fixture
def gdf_single_square_2():
    """Its translated 1, 1 from gdf_single_square_1
    Also this is only 80% H123
    """
    return gpd.GeoDataFrame(
        data={
            "Habtype1": ["H123"],
            "Perc1": [80],
            "Habtype2": ["H234"],
            "Perc2": [20],
        },
        geometry=[Polygon([(10, 10), (30, 10), (30, 30), (10, 30)])],
    )


def test_parse(gdf):
    """Test that parsing returns a geodataframe with a single column, called hab_perc"""
    result = parse_habitat_percentages(gdf)
    expected = [
        {"H123": 80, "H234": 20},
        {"H123": 20, "H234": 80},
        {"H345": 40, "H123": 40, "H234": 20},
        {"H456": 100},
    ]
    assert isinstance(result, gpd.GeoDataFrame)
    assert result.columns.tolist() == ["hab_perc", "geometry"]
    print(result["hab_perc"].tolist())
    assert result["hab_perc"].tolist() == expected
    assert result.geometry.equals(gdf.geometry)


def test_spatial_join(gdf_single_square_1, gdf_single_square_2):
    gdf_pred = parse_habitat_percentages(gdf_single_square_1)
    gdf_true = parse_habitat_percentages(gdf_single_square_2)

    gdf_combined = spatial_join(gdf_pred, gdf_true, how="intersection")
    assert len(gdf_combined) == 1
    assert gdf_combined["pred_hab_perc"].tolist() == [{"H123": 100}]
    assert gdf_combined["true_hab_perc"].tolist() == [{"H123": 80, "H234": 20}]
    assert gdf_combined.geometry.iloc[0] == Polygon(
        [(20, 20), (20, 10), (10, 10), (10, 20)]
    )

    gdf_combined = spatial_join(gdf_pred, gdf_true, how="include_uncharted")
    assert len(gdf_combined) == 3
    assert gdf_combined["pred_hab_perc"].tolist() == [
        {"H123": 100},
        {"H123": 100},
        {"ONGEKARTEERD": 100},
    ]
    assert gdf_combined["true_hab_perc"].tolist() == [
        {"H123": 80, "H234": 20},
        {"ONGEKARTEERD": 100},
        {"H123": 80, "H234": 20},
    ]


def test_voeg_percentage_correct_toe(gdf_single_square_1, gdf_single_square_2):
    gdf_pred = parse_habitat_percentages(gdf_single_square_1)
    gdf_true = parse_habitat_percentages(gdf_single_square_2)
    gdf_combined = spatial_join(gdf_pred, gdf_true, how="intersection")

    gdf = voeg_correctheid_toe_aan_df(gdf_combined)
    assert gdf["percentage_correct"].tolist() == [80]
    assert gdf.area.tolist() == [100]
    assert gdf["oppervlakte_correct"].tolist() == [80 * 100]


def test_bereken_percentage_correct():
    # damn waarom verzint copilot niet tot 100 optellende percentages..
    # anyhow, moet werken voor arbitraire percentages
    habs_pred = {"H123": 80, "H234": 20, "H345": 40}
    habs_true = {"H123": 70, "H345": 50}
    assert bereken_percentage_correct(habs_pred, habs_true) == 110

    habs_pred = {"H123": 20, "H234": 80, "H345": 40}
    habs_true = {"H123": 30, "H234": 70, "H345": 50}
    assert bereken_percentage_correct(habs_pred, habs_true) == 130

    habs_pred = {"H123": 80, "H234": 20, "H345": 40}
    habs_true = {"H123": 0, "H234": 0, "H345": 0}
    assert bereken_percentage_correct(habs_pred, habs_true) == 0


def test_bereken_percentage_confusion_matrix():
    habs_pred = {"H123": 50, "H234": 20, "H345": 30}
    habs_true = {"H123": 70, "H345": 30}

    expected = pd.DataFrame(
        [
            {"pred_hab": "H123", "true_hab": "H123", "percentage": 50},
            {"pred_hab": "H345", "true_hab": "H345", "percentage": 30},
            {"pred_hab": "H234", "true_hab": "H123", "percentage": 20},
        ]
    )
    result = bereken_percentage_confusion_matrix(habs_pred, habs_true)
    assert result.equals(expected)


def test_full_conf_matrix(gdf_single_square_1, gdf_single_square_2):
    gdf_pred = parse_habitat_percentages(gdf_single_square_1)
    gdf_true = parse_habitat_percentages(gdf_single_square_2)
    gdf_combined = spatial_join(gdf_pred, gdf_true, how="intersection")

    result = bereken_volledige_conf_matrix(gdf_combined)
    expected = pd.DataFrame(
        {
            "H123": [8000.0, 0],
            "H234": [
                2000.0,
                0,
            ],
        },
        index=["H123", "H234"],
    )
    assert result.equals(expected)