import tempfile
from pathlib import Path

import geopandas as gpd
import pytest

from veg2hab.constants import WWL_PATH
from veg2hab.io.cli import CLIInterface
from veg2hab.vegkartering import Kartering, VegTypeInfo, ingest_vegtype
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

    access_kartering = Kartering.from_access_db(
        shape_path, shape_elm_id_column, csvs_path
    )
    access_kartering.gdf = access_kartering.gdf.iloc[:10]
    return access_kartering


def apply_wwl(kartering: Kartering) -> Kartering:
    wwl = WasWordtLijst.from_excel(WWL_PATH)
    kartering.apply_wwl(wwl)
    return kartering


def test_equivalency(kartering):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = str(temp_dir)

        kartering = apply_wwl(kartering)
        editable_vegtype = kartering.to_editable_vegtypes()
        editable_vegtype.to_file(temp_dir + "/vegkartering.gpkg", driver="GPKG")

        editable_vegtype2 = gpd.read_file(temp_dir + "/vegkartering.gpkg")
        reconstructed_kartering = Kartering.from_editable_vegtypes(editable_vegtype2)
        assert kartering.gdf.equals(reconstructed_kartering.gdf)
