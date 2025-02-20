import subprocess
import tempfile
from pathlib import Path

import geopandas as gpd
import pyodbc
import pytest

from veg2hab import constants
from veg2hab.bronnen import FGR, LBK, Bodemkaart, OudeBossenkaart
from veg2hab.constants import WWL_PATH
from veg2hab.definitietabel import DefinitieTabel
from veg2hab.io.cli import CLIInterface
from veg2hab.vegkartering import Kartering
from veg2hab.waswordtlijst import WasWordtLijst

CLIInterface.get_instance()


@pytest.fixture
def kartering():
    shape_path = Path(__file__).parent.joinpath(
        "../data/notebook_data/Rottige_Meenthe_Brandemeer_2013/vlakken.shp"
    )
    csvs_path = Path(__file__).parent.joinpath(
        "../data/notebook_data/Rottige_Meenthe_Brandemeer_2013/864_RottigeMeenthe2013.mdb"
    )
    shape_elm_id_column = "ElmID"

    try:
        access_kartering = Kartering.from_access_db(
            shape_path, shape_elm_id_column, csvs_path
        )
    except (RuntimeError, pyodbc.InterfaceError):
        pytest.skip(
            "Could not load kartering, probably because 'mdb-export / microsoft access driver' is not installed"
        )

    access_kartering.gdf = access_kartering.gdf.iloc[:10]
    return access_kartering


def apply_wwl(kartering: Kartering) -> Kartering:
    wwl = WasWordtLijst.from_excel(WWL_PATH)
    kartering.apply_wwl(wwl)
    return kartering


def to_habtypekaart(kartering: Kartering) -> Kartering:
    mask = kartering.get_geometry_mask()
    deftabel = DefinitieTabel.from_excel(Path(constants.DEFTABEL_PATH))
    fgr = FGR(Path(constants.FGR_PATH))
    bodemkaart = Bodemkaart.from_file(
        path=Path(__file__).parent.joinpath("../data/bronbestanden/bodemkaart.gpkg"),
        mask=mask,
    )
    lbk = LBK.from_file(
        path=Path(__file__).parent.joinpath("../data/bronbestanden/lbk.gpkg"), mask=mask
    )
    obk = OudeBossenkaart(Path(constants.OUDE_BOSSENKAART_PATH))

    kartering.apply_deftabel(deftabel)

    kartering.bepaal_mits_habitatkeuzes(fgr, bodemkaart, lbk, obk)
    return kartering


def test_equivalency_vegkart(kartering):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = str(temp_dir)

        kartering = apply_wwl(kartering)
        editable_vegtype = kartering.to_editable_vegtypes()
        editable_vegtype.to_file(temp_dir + "/vegkartering.gpkg", driver="GPKG")

        editable_vegtype2 = gpd.read_file(temp_dir + "/vegkartering.gpkg")
        reconstructed_kartering = Kartering.from_editable_vegtypes(editable_vegtype2)
        assert kartering.gdf.equals(reconstructed_kartering.gdf)


def test_equivalency_habkart(kartering):
    kartering = apply_wwl(kartering)
    kartering = to_habtypekaart(kartering)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = str(temp_dir)

        editable_habtype = kartering.to_editable_habtypes()
        editable_habtype.to_file("habkartering.gpkg", driver="GPKG")

        editable_habtype2 = gpd.read_file("habkartering.gpkg")
        reconstructed_kartering = Kartering.from_editable_habtypes(editable_habtype2)
        assert set(kartering.gdf.columns) == set(reconstructed_kartering.gdf.columns)
        assert (kartering.gdf.index == reconstructed_kartering.gdf.index).all()

        # we need to reorder the columns to compare.
        assert kartering.gdf.equals(reconstructed_kartering.gdf[kartering.gdf.columns])

        kartering.gdf == reconstructed_kartering.gdf[kartering.gdf.columns]

        kartering.gdf.iloc[0].HabitatVoorstel[0][0] == reconstructed_kartering.gdf[
            kartering.gdf.columns
        ].iloc[0].HabitatVoorstel[0][0]
