from pathlib import Path

import geopandas as gpd
import pytest

from veg2hab.constants import WWL_PATH
from veg2hab.vegkartering import Kartering, VegTypeInfo, ingest_vegtype
from veg2hab.waswordtlijst import WasWordtLijst


@pytest.fixture
def kartering():

    shape_path = Path("../data/notebook_data/Rottige_Meenthe_Brandemeer_2013/vlakken.shp")
    csvs_path = Path("../data/notebook_data/Rottige_Meenthe_Brandemeer_2013/864_RottigeMeenthe2013.mdb")
    shape_elm_id_column = "ElmID"

    access_kartering = Kartering.from_access_db(shape_path, shape_elm_id_column, csvs_path)

    return access_kartering.iloc[:10]


def apply_wwl(kartering: Kartering):
    wwl = WasWordtLijst.from_excel(WWL_PATH)
    kartering.apply_wwl(wwl)
    return kartering


def test_equivalency(kartering):
    kartering = apply_wwl(kartering)
    editable_vegtype = kartering.to_editable_vegtypen()
    reconstructed_kartering = kartering.from_editable_vegtypen(editable_vegtype)
    assert kartering.equals(reconstructed_kartering)


