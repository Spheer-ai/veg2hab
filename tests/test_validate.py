import math

import geopandas as gpd
import pandas as pd
from pytest import fixture, raises
from shapely.geometry import Polygon

from veg2hab.validation import (
    bereken_F1_per_habtype,
    bereken_gemiddelde_F1,
    bereken_percentage_confusion_matrix,
    bereken_percentage_correct,
    bereken_totaal_from_dict_col,
    bereken_totaal_succesvol_omgezet,
    bereken_volledige_conf_matrix,
    parse_habitat_percentages,
    spatial_join,
    voeg_correctheid_toe_aan_df,
)


@fixture
def gdf():
    return gpd.GeoDataFrame(
        # in principle this is invalid data.
        # They should be ordered by percentage (and habtype 0 is alway last)
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
    """Its translated 10, 10 from gdf_single_square_1
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


@fixture
def gdf_pred_only_spatial_joined():
    return gpd.GeoDataFrame(
        data={
            "pred_hab_perc": [
                {"H123": 100},
                {"H123": 70, "HXXXX": 30},
                {"H0000": 50, "HXXXX": 50},
            ],
            "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])] * 3,
        }
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
    assert result["hab_perc"].tolist() == expected
    assert result.geometry.equals(gdf.geometry)


def test_parse_with_split_equally(gdf):
    """Test that parsing returns a geodataframe with a single column, called hab_perc"""
    result = parse_habitat_percentages(
        gdf,
        percentage_cols_regex=None,
        how_to_handle_missing_percentages="split_equally",
    )
    expected = [
        {"H123": 50, "H234": 50},
        {"H123": 50, "H234": 50},
        {"H345": 100 / 3, "H123": 100 / 3, "H234": 100 / 3},
        {"H456": 100},
    ]
    assert result["hab_perc"].tolist() == expected


def test_parse_with_select_first(gdf):
    """Test that parsing returns a geodataframe with a single column, called hab_perc"""
    result = parse_habitat_percentages(
        gdf,
        percentage_cols_regex=None,
        how_to_handle_missing_percentages="select_first",
    )
    expected = [
        {"H123": 100},
        {"H123": 100},
        {"H345": 100},
        {"H456": 100},
    ]
    assert result["hab_perc"].tolist() == expected


def test_with_no_habtypes(gdf):
    """Test that it doesn't fail if all Habtypes are set to None."""
    gdf.loc[0, ["Habtype1", "Habtype2", "Habtype3"]] = None
    gdf.loc[0, ["Perc1", "Perc2", "Perc3"]] = 0
    results = parse_habitat_percentages(gdf)
    assert results.loc[0, "hab_perc"] == {"H0000": 100}
    results = parse_habitat_percentages(
        gdf,
        percentage_cols_regex=None,
        how_to_handle_missing_percentages="select_first",
    )
    assert results.loc[0, "hab_perc"] == {"H0000": 100}
    results = parse_habitat_percentages(
        gdf,
        percentage_cols_regex=None,
        how_to_handle_missing_percentages="split_equally",
    )
    assert results.loc[0, "hab_perc"] == {"H0000": 100}


def test_with_duplicate_habtypes(gdf):
    """Test that it doesn't fail if the same habtype is present multiple times
    This could be the result of different quality or predicting HXXXX multiple times
    """
    gdf.loc[0, ["Habtype1", "Habtype2", "Habtype3"]] = ["H123", "H123", None]
    gdf.loc[0, ["Perc1", "Perc2", "Perc3"]] = [60, 40, 0]
    results = parse_habitat_percentages(gdf)
    assert results.loc[0, "hab_perc"] == {"H123": 100}

    gdf.loc[0, ["Habtype1", "Habtype2", "Habtype3"]] = ["H123", "H123", "H234"]
    gdf.loc[0, ["Perc1", "Perc2", "Perc3"]] = [50, 40, 10]
    results = parse_habitat_percentages(gdf)
    assert results.loc[0, "hab_perc"] == {"H123": 90, "H234": 10}

    gdf.loc[0, ["Habtype1", "Habtype2", "Habtype3"]] = ["H123", "H123", "H234"]
    gdf.loc[0, ["Perc1", "Perc2", "Perc3"]] = [50, 40, 10]
    results = parse_habitat_percentages(
        gdf,
        percentage_cols_regex=None,
        how_to_handle_missing_percentages="split_equally",
    )
    assert results.loc[0, "hab_perc"] == {"H123": 50, "H234": 50}


def test_with_add_kwaliteit(gdf):
    # expect value error since there are no kwaliteit columns
    with raises(ValueError):
        parse_habitat_percentages(gdf, add_kwaliteit=True)

    gdf["Kwal1"] = ["G", "M", "X", None]
    gdf["Kwal2"] = ["G", "X", "M", None]
    gdf["Kwal3"] = [None, None, "G", "M"]
    results = parse_habitat_percentages(gdf, add_kwaliteit=True).kwal_perc

    expected = pd.Series(
        [
            {"Goed": 100},
            {"Matig": 20, "Nvt": 80},
            {"Nvt": 40, "Matig": 40, "Goed": 20},
            {"Matig": 100},
        ],
    )

    assert results.equals(expected)


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


def test_bereken_percentage_confusion_matrix_with_invalid_inputs():
    habs_pred = {"HXXXX": 10.0, "H0000": 10.0}
    habs_true = {"H0000": 100}

    expected = pd.DataFrame(
        [
            {"pred_hab": "H0000", "true_hab": "H0000", "percentage": 10.0},
            {"pred_hab": "HXXXX", "true_hab": "H0000", "percentage": 10.0},
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
            "H123": [0.008, 0],
            "H234": [
                0.002,
                0,
            ],
        },
        index=["H123", "H234"],
    )
    assert result.equals(expected)


def test_bereken_totaal_succesvol_omgezet(gdf_pred_only_spatial_joined):
    assert (
        bereken_totaal_succesvol_omgezet(gdf_pred_only_spatial_joined, "percentage")
        == 2.2
    )
    assert math.isclose(
        bereken_totaal_succesvol_omgezet(gdf_pred_only_spatial_joined, "area"),
        0.022,
        rel_tol=1e-9,
    )


def test_bereken_totaal_percentage_from_dict(gdf_pred_only_spatial_joined):
    assert bereken_totaal_from_dict_col(
        gdf_pred_only_spatial_joined, "pred_hab_perc", "percentage"
    ) == {"H123": 1.7, "HXXXX": 0.8, "H0000": 0.5}
    assert bereken_totaal_from_dict_col(
        gdf_pred_only_spatial_joined, "pred_hab_perc", "area"
    ) == {"H123": 0.0170, "HXXXX": 0.0080, "H0000": 0.0050}


def test_F1():
    df = pd.DataFrame(
        data={
            "H0000": [3, 1, 1, 0],
            "H6430A": [0, 3, 0, 0],
            "H7140A": [0, 0, 3, 0],
            "HXXXX": [4, 1, 1, 0],
        },
        index=["H0000", "H6430A", "H7140A", "HXXXX"],
    )

    expected = {"H0000": 0.5, "H6430A": 0.75, "H7140A": 0.75}
    result = bereken_F1_per_habtype(df)

    assert expected.keys() == result.keys()
    for key in expected:
        assert math.isclose(expected[key], result[key], rel_tol=1e-9)

    expected_macro = sum(expected.values()) / 3
    result_macro = bereken_gemiddelde_F1(df)
    assert math.isclose(expected_macro, result_macro, rel_tol=1e-9)
