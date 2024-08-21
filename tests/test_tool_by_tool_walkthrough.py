import os

import geopandas as gpd
import pandas as pd
import pyodbc
import pytest
from pytest import fixture

from veg2hab.criteria import OverrideCriterium
from veg2hab.enums import MaybeBoolean
from veg2hab.io.common import (
    AccessDBInputs,
    ApplyDefTabelInputs,
    ApplyFunctioneleSamenhangInputs,
    ApplyMozaiekInputs,
)
from veg2hab.main import run

IS_WINDOWS = os.name == "nt"


@fixture
def steps() -> tuple:
    step_1 = AccessDBInputs(
        shapefile="data/notebook_data/Rottige_Meenthe_Brandemeer_2013/vlakken.shp",
        elmid_col="ElmID",
        access_mdb_path="data/notebook_data/Rottige_Meenthe_Brandemeer_2013/864_RottigeMeenthe2013.mdb",
        welke_typologie="SBB",
        output="data/tool_by_tool/1.gpkg",
    )

    step_3 = ApplyDefTabelInputs(
        shapefile=str(step_1.output), output="data/tool_by_tool/3.gpkg"
    )

    step_4 = ApplyMozaiekInputs(
        shapefile=str(step_3.output), output="data/tool_by_tool/4.gpkg"
    )

    step_5 = ApplyFunctioneleSamenhangInputs(
        shapefile=str(step_4.output), output="data/tool_by_tool/5.gpkg"
    )

    return step_1, step_3, step_4, step_5


@pytest.mark.timed
@pytest.mark.slow
@pytest.mark.skipif(
    IS_WINDOWS, reason="Skip on windows because of (absence of) microsoft access driver"
)
def test_full_standaard_run(steps):
    step_1, step_3, step_4, step_5 = steps
    run(step_1)
    run(step_3)
    run(step_4)
    run(step_5)

    expected_1 = pd.Series(
        {
            "HXXXX": 1030,
            "H7140_B": 502,
            "H0000": 389,
            "H4010_B": 16,
            "H7140_A": 12,
        }
    )

    expected_2 = pd.Series(
        {
            "H0000": 545,
            "HXXXX": 379,
            "H7140_B": 212,
            "H4010_B": 6,
            "H7140_A": 3,
        }
    )

    expected_3 = pd.Series(
        {
            "H0000": 263,
            "HXXXX": 79,
            "H7140_B": 18,
            "H4010_B": 1,
        }
    )

    expected_4 = pd.Series(
        {
            "H0000": 34,
            "HXXXX": 7,
            "H7140_B": 1,
        }
    )

    expected_5 = pd.Series(
        {
            "H0000": 2,
        }
    )

    gdf = gpd.read_file(step_5.output)

    assert gdf.Habtype1.value_counts().equals(expected_1)
    assert gdf.Habtype2.value_counts().equals(expected_2)
    assert gdf.Habtype3.value_counts().equals(expected_3)
    assert gdf.Habtype4.value_counts().equals(expected_4)
    assert gdf.Habtype5.value_counts().equals(expected_5)


@pytest.mark.slow
@pytest.mark.skipif(
    IS_WINDOWS, reason="Skip on windows because of (absence of) microsoft access driver"
)
def test_changes_in_vegtype(steps):
    step_1, step_3, step_4, step_5 = steps
    run(step_1)
    gdf = gpd.read_file(step_1.output)
    # We hebben enkel een paar regels nodig
    gdf = gdf.head(10)
    gdf.loc[0, "EDIT_SBB2"] = "1a1a"
    gdf.loc[0, "EDIT_VvN2"] = "1aa1a"
    gdf.to_file(step_1.output, driver="GPKG", layer="main")
    run(step_3)
    run(step_4)
    run(step_5)
    done = gpd.read_file(step_5.output)
    assert done.iloc[0].SBB2 == "1a1a"
    assert done.iloc[0].VvN2 == "1aa1a"


@pytest.mark.slow
@pytest.mark.skipif(
    IS_WINDOWS, reason="Skip on windows because of (absence of) microsoft access driver"
)
def test_changes_in_habtype(steps):
    step_1, step_3, step_4, step_5 = steps
    run(step_1)
    gdf = gpd.read_file(step_1.output)
    # We hebben enkel een paar regels nodig
    gdf = gdf.head(10)
    gdf.to_file(step_1.output, driver="GPKG", layer="main")
    run(step_3)
    gdf = gpd.read_file(step_3.output)
    gdf.loc[0, "EDIT_Habtype2"] = "H1234"
    gdf.loc[0, "EDIT_Kwal2"] = "M"
    gdf.to_file(step_3.output, driver="GPKG", layer="main")
    run(step_4)
    gdf = gpd.read_file(step_4.output)
    gdf.loc[1, "EDIT_Habtype1"] = "H4321"
    gdf.loc[1, "EDIT_Kwal1"] = "G"
    gdf.to_file(step_4.output, driver="GPKG", layer="main")
    run(step_5)
    done = gpd.read_file(step_5.output)
    assert done.iloc[0].Habtype2 == "H1234"
    assert done.iloc[0].Kwal2 == "M"
    assert done.iloc[1].Habtype1 == "H4321"
    assert done.iloc[1].Kwal1 == "G"


@pytest.mark.slow
@pytest.mark.skipif(
    IS_WINDOWS, reason="Skip on windows because of (absence of) microsoft access driver"
)
def test_mits_override(steps):
    step_1, step_3, step_4, step_5 = steps

    run(step_1)
    gdf = gpd.read_file(step_1.output)
    # We hebben enkel een paar regels nodig
    gdf = gdf.head(10)
    gdf.to_file(step_1.output, driver="GPKG", layer="main")

    # Normal case
    run(step_3)
    run(step_4)
    run(step_5)

    gdf = gpd.read_file(step_5.output)

    assert gdf.Habtype1.iloc[4] == "HXXXX"
    assert gdf.Habtype1.iloc[8] == "HXXXX"

    # Override case

    # "mits in vochtige duinvalleien" wordt normaal MaybeBoolean.CANNOT_BE_AUTOMATED
    # Dus dit wordt normaal HXXXX, maar nu gebruiken we een geometry OverrideCriterium
    # met als override_geometry die van vlak iloc[4], dus ipv HXXXX krijgen we H2190_D voor vlak iloc[4]
    #
    # Dezelfde mits wordt ook gevonden bij vlak iloc[8] (buiten de override_geometry dus),
    # dus daar wordt het H0000 ipv HXXXX, want truth_value_outside is MaybeBoolean.FALSE
    crit = OverrideCriterium(
        mits="mits in vochtige duinvalleien",
        truth_value=MaybeBoolean.TRUE,
        override_geometry=gdf.geometry.iloc[[4]],
        truth_value_outside=MaybeBoolean.FALSE,
    )

    override_dict = {"mits in vochtige duinvalleien": crit}

    step_3 = ApplyDefTabelInputs(
        shapefile=str(step_1.output),
        output="data/tool_by_tool/3.gpkg",
        override_dict=override_dict,
    )

    run(step_3)
    run(step_4)
    run(step_5)

    gdf = gpd.read_file(step_5.output)

    assert gdf.Habtype1.iloc[4] == "H2190_D"
    assert gdf.Habtype1.iloc[8] == "H0000"
