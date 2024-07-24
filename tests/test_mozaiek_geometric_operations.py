import logging

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from veg2hab.criteria import GeenCriterium
from veg2hab.enums import KeuzeStatus, Kwaliteit, MatchLevel
from veg2hab.habitat import HabitatKeuze, HabitatVoorstel
from veg2hab.io.cli import CLIInterface
from veg2hab.mozaiek import (
    GeenMozaiekregel,
    StandaardMozaiekregel,
    construct_elmid_omringd_door_gdf,
    make_buffered_boundary_overlay_gdf,
)
from veg2hab.vegetatietypen import VvN
from veg2hab.vegkartering import VegTypeInfo

CLIInterface.get_instance()

"""
Test layout

 Habtypen     Elmid
+---+---+   +---+---+
| H1| H2|   | 1 | 2 |
|   +---+   |   +---+
| H1| H2|   | 1 | 3 |
|   +---+   |   +---+
| H1| H3|   | 1 | 4 |
+---+---+   +---+---+

We bufferen in deze tests met 0 zodat de getallen mooi rond blijven.
Dit betekend wel dat vlakken zichzelf ook snijden en dus altijd
voor een extra 100% door hun eigen habitattype omringd worden.
"""


@pytest.fixture
def gdf():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H1",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=StandaardMozaiekregel(
                kwalificerend_habtype="H1",
                ook_mozaiekvegetaties=False,
                alleen_goede_kwaliteit=True,
                ook_als_rand_langs=False,
            ),
            match_level=MatchLevel.NO_MATCH,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H2",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H2",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H3",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        ),
    ]

    return gpd.GeoDataFrame(
        {
            "HabitatKeuze": [
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H1",
                        kwaliteit=Kwaliteit.GOED,
                        opmerking="",
                        mits_opmerking="",
                        mozaiek_opmerking="",
                        debug_info="",
                        habitatvoorstellen=[voorstellen[0]],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H2",
                        kwaliteit=Kwaliteit.GOED,
                        opmerking="",
                        mits_opmerking="",
                        mozaiek_opmerking="",
                        debug_info="",
                        habitatvoorstellen=[voorstellen[1]],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H2",
                        kwaliteit=Kwaliteit.GOED,
                        opmerking="",
                        mits_opmerking="",
                        mozaiek_opmerking="",
                        debug_info="",
                        habitatvoorstellen=[voorstellen[2]],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H3",
                        kwaliteit=Kwaliteit.GOED,
                        opmerking="",
                        mits_opmerking="",
                        mozaiek_opmerking="",
                        debug_info="",
                        habitatvoorstellen=[voorstellen[3]],
                    )
                ],
            ],
            "ElmID": [1, 2, 3, 4],
            "VegTypeInfo": [
                [VegTypeInfo.from_str_vegtypes(percentage=100, VvN_strings=["1aa1"])],
                [VegTypeInfo.from_str_vegtypes(percentage=100, VvN_strings=["2bb2"])],
                [VegTypeInfo.from_str_vegtypes(percentage=100, VvN_strings=["3cc3"])],
                [VegTypeInfo.from_str_vegtypes(percentage=100, VvN_strings=["4dd4"])],
            ],
            "HabitatVoorstel": [
                [[voorstellen[0]]],
                [[voorstellen[1]]],
                [[voorstellen[2]]],
                [[voorstellen[3]]],
            ],
            "geometry": [
                Polygon([(0, 0), (1, 0), (1, 3), (0, 3), (0, 0)]),
                Polygon([(1, 2), (2, 2), (2, 3), (1, 3), (1, 2)]),
                Polygon([(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)]),
                Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]),
            ],
        }
    )


def test_value_error_buffer_less_than_zero(gdf):
    with pytest.raises(ValueError):
        make_buffered_boundary_overlay_gdf(gdf, buffer=-0.1)


def test_warning_buffer_equals_zero(gdf, caplog):
    caplog.set_level(logging.WARNING)
    make_buffered_boundary_overlay_gdf(gdf, buffer=0)
    assert "Buffer is 0. Dit kan leiden tot onverwachte resultaten." in caplog.text


def test_single_shape(gdf):
    # Enkel 1
    pre = gdf[gdf["ElmID"].isin([1])]
    post = pd.DataFrame(
        {
            "buffered_ElmID": [1.0],
            "ElmID": [1],
            "habtype": ["H1"],
            "kwaliteit": [Kwaliteit.GOED],
            "vegtypen": [[VvN.from_code("1aa1")]],
            "complexdeel_percentage": [100.0],
            "omringing_percentage": [100.0],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze", "VegTypeInfo"]],
        on="ElmID",
        how="left",
    )
    assert (construct_elmid_omringd_door_gdf(overlayed) == post).all().all()


def test_single_shape_matig_mozaiek(gdf):
    # Enkel 1
    pre = gdf[gdf["ElmID"].isin([1])]
    pre["HabitatKeuze"].iloc[0][0].kwaliteit = Kwaliteit.MATIG
    post = pd.DataFrame(
        {
            "buffered_ElmID": [1.0],
            "ElmID": [1],
            "habtype": ["H1"],
            "kwaliteit": [Kwaliteit.MATIG],
            "vegtypen": [[VvN.from_code("1aa1")]],
            "complexdeel_percentage": [100.0],
            "omringing_percentage": [100.0],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze", "VegTypeInfo"]],
        on="ElmID",
        how="left",
    )
    assert (construct_elmid_omringd_door_gdf(overlayed) == post).all().all()


def test_two_shapes(gdf):
    pass
    # 1 en 2
    pre = gdf[gdf["ElmID"].isin([1, 2])]
    post = pd.DataFrame(
        {
            "buffered_ElmID": [1.0, 1.0],
            "ElmID": [1, 2],
            "habtype": ["H1", "H2"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [[VvN.from_code("1aa1")], [VvN.from_code("2bb2")]],
            "complexdeel_percentage": [100.0, 100.0],
            "omringing_percentage": [100.0, 12.5],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze", "VegTypeInfo"]],
        on="ElmID",
        how="left",
    )
    assert (construct_elmid_omringd_door_gdf(overlayed) == post).all().all()


def test_habtype_percentage_addition(gdf):
    # 1 en 2 en 3
    pre = gdf[gdf["ElmID"].isin([1, 2, 3])]
    post = pd.DataFrame(
        # construct it from above commented dataframe
        {
            "buffered_ElmID": [1.0, 1.0, 1.0],
            "ElmID": [1, 2, 3],
            "habtype": ["H1", "H2", "H2"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [
                [VvN.from_code("1aa1")],
                [VvN.from_code("2bb2")],
                [VvN.from_code("3cc3")],
            ],
            "complexdeel_percentage": [100.0, 100.0, 100.0],
            "omringing_percentage": [100.0, 12.5, 12.5],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze", "VegTypeInfo"]],
        on="ElmID",
        how="left",
    )
    assert (construct_elmid_omringd_door_gdf(overlayed) == post).all().all()


def test_two_habtypes(gdf):
    # 1 en 3 en 4
    pre = gdf[gdf["ElmID"].isin([1, 3, 4])]
    post = pd.DataFrame(
        {
            "buffered_ElmID": [1.0, 1.0, 1.0],
            "ElmID": [1, 3, 4],
            "habtype": ["H1", "H2", "H3"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [
                [VvN.from_code("1aa1")],
                [VvN.from_code("3cc3")],
                [VvN.from_code("4dd4")],
            ],
            "complexdeel_percentage": [100.0, 100.0, 100.0],
            "omringing_percentage": [100.0, 12.5, 12.5],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze", "VegTypeInfo"]],
        on="ElmID",
        how="left",
    )
    assert (construct_elmid_omringd_door_gdf(overlayed) == post).all().all()


def test_all_shapes(gdf):
    # 1 en 2 en 3 en 4
    pre = gdf
    post = pd.DataFrame(
        {
            "buffered_ElmID": [1.0, 1.0, 1.0, 1.0],
            "ElmID": [1, 2, 3, 4],
            "habtype": ["H1", "H2", "H2", "H3"],
            "kwaliteit": [
                Kwaliteit.GOED,
                Kwaliteit.GOED,
                Kwaliteit.GOED,
                Kwaliteit.GOED,
            ],
            "vegtypen": [
                [VvN.from_code("1aa1")],
                [VvN.from_code("2bb2")],
                [VvN.from_code("3cc3")],
                [VvN.from_code("4dd4")],
            ],
            "complexdeel_percentage": [100.0, 100.0, 100.0, 100.0],
            "omringing_percentage": [100.0, 12.5, 12.5, 12.5],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze", "VegTypeInfo"]],
        on="ElmID",
        how="left",
    )
    assert (construct_elmid_omringd_door_gdf(overlayed) == post).all().all()


def test_multiple_mozaiek_present_shapes(gdf):
    # 1 en 2, beide met mozaiekregel
    pre = gdf[gdf["ElmID"].isin([1, 2])].copy()
    # Omdat de voorstellen in HabitatKeuze uit dezelfde list komen hoeven we enkel HabitatVoorstel te updaten.
    nieuwe_regel = StandaardMozaiekregel(
        kwalificerend_habtype="H2",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    pre["HabitatKeuze"].iloc[1][0].habitatvoorstellen[0].mozaiek = nieuwe_regel
    pre["HabitatVoorstel"].iloc[1][0][0].mozaiek = nieuwe_regel

    post = pd.DataFrame(
        {
            "buffered_ElmID": [1.0, 2.0, 1.0, 2.0],
            "ElmID": [1, 1, 2, 2],
            "habtype": ["H1", "H1", "H2", "H2"],
            "kwaliteit": [
                Kwaliteit.GOED,
                Kwaliteit.GOED,
                Kwaliteit.GOED,
                Kwaliteit.GOED,
            ],
            "vegtypen": [
                [VvN.from_code("1aa1")],
                [VvN.from_code("1aa1")],
                [VvN.from_code("2bb2")],
                [VvN.from_code("2bb2")],
            ],
            "complexdeel_percentage": [100.0, 100.0, 100.0, 100.0],
            "omringing_percentage": [100.0, 25.0, 12.5, 100.0],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze", "VegTypeInfo"]],
        on="ElmID",
        how="left",
    )
    assert (construct_elmid_omringd_door_gdf(overlayed) == post).all().all()
