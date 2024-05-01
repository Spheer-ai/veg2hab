import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from veg2hab.criteria import GeenCriterium
from veg2hab.enums import KeuzeStatus, Kwaliteit
from veg2hab.habitat import HabitatKeuze, HabitatVoorstel
from veg2hab.mozaiek import (
    GeenMozaiekregel,
    StandaardMozaiekregel,
    calc_mozaiek_percentages_from_overlay_gdf,
    make_buffered_boundary_overlay_gdf,
)

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
                habtype="H1",
                alleen_zelfstandig=True,
                alleen_goede_kwaliteit=True,
            ),
            match_level=None,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H2",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=None,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H2",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=None,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H3",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=None,
        ),
    ]

    return gpd.GeoDataFrame(
        {
            "HabitatKeuze": [
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
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
                        status=KeuzeStatus.DUIDELIJK,
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
                        status=KeuzeStatus.DUIDELIJK,
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
                        status=KeuzeStatus.DUIDELIJK,
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
            "mozaiek_present": [True, False, False, False],
            "HabitatVoorstel": [
                [
                    [
                        HabitatVoorstel(
                            onderbouwend_vegtype=None,
                            vegtype_in_dt=None,
                            habtype="H1",
                            kwaliteit=Kwaliteit.GOED,
                            idx_in_dt=None,
                            mits=GeenCriterium(),
                            mozaiek=StandaardMozaiekregel(
                                habtype="H1",
                                alleen_zelfstandig=True,
                                alleen_goede_kwaliteit=True,
                                ook_als_rand_langs=False,
                            ),
                            match_level=None,
                        )
                    ]
                ],
                [
                    [
                        HabitatVoorstel(
                            onderbouwend_vegtype=None,
                            vegtype_in_dt=None,
                            habtype="H2",
                            kwaliteit=Kwaliteit.GOED,
                            idx_in_dt=None,
                            mits=GeenCriterium(),
                            mozaiek=GeenMozaiekregel(),
                            match_level=None,
                        )
                    ]
                ],
                [
                    [
                        HabitatVoorstel(
                            onderbouwend_vegtype=None,
                            vegtype_in_dt=None,
                            habtype="H2",
                            kwaliteit=Kwaliteit.GOED,
                            idx_in_dt=None,
                            mits=GeenCriterium(),
                            mozaiek=GeenMozaiekregel(),
                            match_level=None,
                        )
                    ]
                ],
                [
                    [
                        HabitatVoorstel(
                            onderbouwend_vegtype=None,
                            vegtype_in_dt=None,
                            habtype="H3",
                            kwaliteit=Kwaliteit.GOED,
                            idx_in_dt=None,
                            mits=GeenCriterium(),
                            mozaiek=GeenMozaiekregel(),
                            match_level=None,
                        )
                    ]
                ],
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


def test_warning_buffer_equals_zero(gdf):
    with pytest.warns(UserWarning):
        make_buffered_boundary_overlay_gdf(gdf, buffer=0)


def test_single_shape(gdf):
    # Enkel 1
    pre = gdf[gdf["ElmID"].isin([1])]
    post = pd.DataFrame(
        {"ElmID": [1], "dict": [{("H1", False, Kwaliteit.GOED): 100.0}]}
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze"]],
        on="ElmID",
        how="left",
    )
    assert (calc_mozaiek_percentages_from_overlay_gdf(overlayed) == post).all().all()


def test_single_shape_matig_mozaiek(gdf):
    # Enkel 1
    pre = gdf[gdf["ElmID"].isin([1])]
    pre["HabitatKeuze"].iloc[0][0].kwaliteit = Kwaliteit.MATIG
    post = pd.DataFrame(
        {"ElmID": [1], "dict": [{("H1", False, Kwaliteit.MATIG): 100.0}]}
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze"]],
        on="ElmID",
        how="left",
    )
    assert (calc_mozaiek_percentages_from_overlay_gdf(overlayed) == post).all().all()


def test_two_shapes(gdf):
    # 1 en 2
    pre = gdf[gdf["ElmID"].isin([1, 2])]
    post = pd.DataFrame(
        {
            "ElmID": [1],
            "dict": [
                {
                    ("H1", False, Kwaliteit.GOED): 100.0,
                    ("H2", True, Kwaliteit.GOED): 12.5,
                },
            ],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze"]],
        on="ElmID",
        how="left",
    )
    assert (calc_mozaiek_percentages_from_overlay_gdf(overlayed) == post).all().all()


def test_habtype_percentage_addition(gdf):
    # 1 en 2 en 3
    pre = gdf[gdf["ElmID"].isin([1, 2, 3])]
    post = pd.DataFrame(
        {
            "ElmID": [1],
            "dict": [
                {
                    ("H1", False, Kwaliteit.GOED): 100.0,
                    ("H2", True, Kwaliteit.GOED): 25.0,
                },
            ],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze"]],
        on="ElmID",
        how="left",
    )
    assert (calc_mozaiek_percentages_from_overlay_gdf(overlayed) == post).all().all()


def test_two_habtypes(gdf):
    # 1 en 3 en 4
    pre = gdf[gdf["ElmID"].isin([1, 3, 4])]
    post = pd.DataFrame(
        {
            "ElmID": [1],
            "dict": [
                {
                    ("H1", False, Kwaliteit.GOED): 100.0,
                    ("H2", True, Kwaliteit.GOED): 12.5,
                    ("H3", True, Kwaliteit.GOED): 12.5,
                },
            ],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze"]],
        on="ElmID",
        how="left",
    )
    assert (calc_mozaiek_percentages_from_overlay_gdf(overlayed) == post).all().all()


def test_all_shapes(gdf):
    # 1 en 2 en 3 en 4
    pre = gdf
    post = pd.DataFrame(
        {
            "ElmID": [1],
            "dict": [
                {
                    ("H1", False, Kwaliteit.GOED): 100.0,
                    ("H2", True, Kwaliteit.GOED): 25.0,
                    ("H3", True, Kwaliteit.GOED): 12.5,
                },
            ],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze"]],
        on="ElmID",
        how="left",
    )
    assert (calc_mozaiek_percentages_from_overlay_gdf(overlayed) == post).all().all()


def test_multiple_mozaiek_present_shapes(gdf):
    # 1 en 2, beide met mozaiekregel
    pre = gdf[gdf["ElmID"].isin([1, 2])].copy()
    pre["HabitatVoorstel"].iloc[1][0][0].mozaiek = StandaardMozaiekregel(
        habtype="H2",
        alleen_zelfstandig=True,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    post = pd.DataFrame(
        {
            "ElmID": [1, 2],
            "dict": [
                {
                    ("H1", False, Kwaliteit.GOED): 100.0,
                    ("H2", False, Kwaliteit.GOED): 12.5,
                },
                {
                    ("H1", False, Kwaliteit.GOED): 25.0,
                    ("H2", False, Kwaliteit.GOED): 100.0,
                },
            ],
        }
    )
    overlayed = make_buffered_boundary_overlay_gdf(pre, buffer=0)
    overlayed = overlayed.merge(
        gdf[["ElmID", "HabitatKeuze"]],
        on="ElmID",
        how="left",
    )
    assert (calc_mozaiek_percentages_from_overlay_gdf(overlayed) == post).all().all()
