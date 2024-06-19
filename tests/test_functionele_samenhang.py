import json
import os

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from veg2hab.enums import KeuzeStatus, Kwaliteit
from veg2hab.functionele_samenhang import (
    UnionFind,
    _cluster_vlakken,
    _extract_elmid_perc_habtype,
    apply_functionele_samenhang,
)
from veg2hab.habitat import HabitatKeuze
from veg2hab.io.cli import CLIInterface
from veg2hab.vegkartering import VegTypeInfo

CLIInterface.get_instance()

"""
       20m                10m
      <--->               <->
+---+       +---+---+---+     +---+
|100|       |100|60 |90 |     |90 |
+---+       +---+---+---+     +---+

"""


@pytest.fixture
def test_gdf():
    # Deze heb ik hier hard gecode omdat anders de test_env_vars_overwrite_config mijn min_area en min_area_default overschrijft
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_EXCEPTIONS"] = json.dumps(
        {
            "H6110": 10,
            "H7220": 10,
            "H2180_A": 1000,
            "H2180_B": 1000,
            "H2180_C": 1000,
            "H9110": 1000,
            "H9120": 1000,
            "H9160_A": 1000,
            "H9160_B": 1000,
            "H9190": 1000,
            "H91D0": 1000,
            "H91E0_A": 1000,
            "H91E0_B": 1000,
            "H91E0_C": 1000,
            "H91F0": 1000,
        }
    )
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = "100"
    os.environ["VEG2HAB_FUNCTIONELE_SAMENHANG_BUFFER_DISTANCES"] = json.dumps(
        [
            (100, 10.01),
            (90, 5.01),
            (50, 0.01),
        ]
    )
    return gpd.GeoDataFrame(
        {
            "ElmID": [1, 2, 3, 4, 5],
            "VegTypeInfo": [
                [VegTypeInfo(SBB=[], VvN=[], percentage=100)],
                [VegTypeInfo(SBB=[], VvN=[], percentage=100)],
                [
                    VegTypeInfo(SBB=[], VvN=[], percentage=60),
                    VegTypeInfo(SBB=[], VvN=[], percentage=40),
                ],
                [
                    VegTypeInfo(SBB=[], VvN=[], percentage=90),
                    VegTypeInfo(SBB=[], VvN=[], percentage=10),
                ],
                [
                    VegTypeInfo(SBB=[], VvN=[], percentage=90),
                    VegTypeInfo(SBB=[], VvN=[], percentage=10),
                ],
            ],
            "HabitatKeuze": [
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    ),
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H4321",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    ),
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    ),
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H4321",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    ),
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    ),
                    HabitatKeuze(
                        status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                        habtype="H4321",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    ),
                ],
            ],
            "geometry": [
                Polygon([(0, 0), (0, 20), (20, 20), (20, 0)]),
                Polygon([(40, 0), (40, 20), (60, 20), (60, 0)]),
                Polygon([(60, 0), (60, 20), (80, 20), (80, 0)]),
                Polygon([(80, 0), (80, 20), (100, 20), (100, 0)]),
                Polygon([(110, 0), (110, 20), (130, 20), (130, 0)]),
            ],
        }
    )


def compare_clusterings(clustering1, clustering2):
    sorted_clustering1 = sorted([sorted(cluster) for cluster in clustering1])
    sorted_clustering2 = sorted([sorted(cluster) for cluster in clustering2])
    return sorted_clustering1 == sorted_clustering2


def test_UnionFind_cluster_pairs():
    clusters = [[1, 2], [2, 3], [2, 4], [5, 5]]
    assert compare_clusterings(UnionFind.cluster_pairs(clusters), [[1, 2, 3, 4], [5]])

    clusters = [[1, 2], [3, 4], [5, 6], [2, 3]]
    assert compare_clusterings(
        UnionFind.cluster_pairs(clusters), [[1, 2, 3, 4], [5, 6]]
    )

    clusters = [[1, 2], [2, 3], [4, 5], [1, 6], [4, 7], [8, 8]]
    assert compare_clusterings(
        UnionFind.cluster_pairs(clusters), [[1, 2, 3, 6], [4, 5, 7], [8]]
    )


def test_extract_elmid_perc_habtype(test_gdf):
    extracted = _extract_elmid_perc_habtype(test_gdf)
    extracted_reference = gpd.GeoDataFrame(
        {
            "identifier": [
                (1, (0,)),
                (2, (0,)),
                (3, (0,)),
                (3, (1,)),
                (4, (0,)),
                (4, (1,)),
                (5, (0,)),
                (5, (1,)),
            ],
            "percentage": [
                100.0,
                100.0,
                60.0,
                40.0,
                90.0,
                10.0,
                90.0,
                10.0,
            ],
            "habtype": [
                "H1234",
                "H1234",
                "H1234",
                "H4321",
                "H1234",
                "H4321",
                "H1234",
                "H4321",
            ],
            "geometry": [
                Polygon([(0, 0), (0, 20), (20, 20), (20, 0)]),
                Polygon([(40, 0), (40, 20), (60, 20), (60, 0)]),
                Polygon([(60, 0), (60, 20), (80, 20), (80, 0)]),
                Polygon([(60, 0), (60, 20), (80, 20), (80, 0)]),
                Polygon([(80, 0), (80, 20), (100, 20), (100, 0)]),
                Polygon([(80, 0), (80, 20), (100, 20), (100, 0)]),
                Polygon([(110, 0), (110, 20), (130, 20), (130, 0)]),
                Polygon([(110, 0), (110, 20), (130, 20), (130, 0)]),
            ],
        }
    )
    assert extracted.equals(extracted_reference)


def test_gdf_cluster_vlakken(test_gdf):
    # normal case
    extracted = _extract_elmid_perc_habtype(test_gdf)
    clustered = _cluster_vlakken(extracted)
    assert compare_clusterings(
        clustered,
        [
            [(1, (0,)), (2, (0,)), (3, (0,)), (4, (0,)), (5, (0,))],
            [(3, (1,))],
            [(4, (1,))],
            [(5, (1,))],
        ],
    )

    # remove ElmID 3
    test_gdf = test_gdf.drop(2)
    extracted = _extract_elmid_perc_habtype(test_gdf)
    clustered = _cluster_vlakken(extracted)
    assert compare_clusterings(
        clustered,
        [[(1, (0,)), (2, (0,))], [(4, (0,)), (5, (0,))], [(4, (1,))], [(5, (1,))]],
    )


def test_functionele_samenhang_fully_one_big_cluster(test_gdf):
    # normal case
    test_gdf = apply_functionele_samenhang(test_gdf)
    assert test_gdf["HabitatKeuze"].iloc[0][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[1][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[2][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[2][1].habtype == "H4321"
    assert test_gdf["HabitatKeuze"].iloc[3][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[3][1].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[4][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[4][1].habtype == "H0000"

    # increase minimum size a bit
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = "1000"
    test_gdf = apply_functionele_samenhang(test_gdf)
    assert test_gdf["HabitatKeuze"].iloc[0][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[1][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[2][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[2][1].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[3][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[3][1].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[4][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[4][1].habtype == "H0000"

    # increase minimum size massively
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = "10000"
    test_gdf = apply_functionele_samenhang(test_gdf)
    assert test_gdf["HabitatKeuze"].iloc[0][0].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[1][0].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[2][0].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[2][1].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[3][0].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[3][1].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[4][0].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[4][1].habtype == "H0000"


def test_combining_of_same_habtype_in_one_shape(test_gdf):
    # Enkel het 60/40 vlak testen, met beide complexdelen H1234
    # Eerst dat ze samen net genoeg zijn
    test_gdf = test_gdf.iloc[[2]]
    test_gdf.HabitatKeuze = [
        [
            HabitatKeuze(
                status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                habtype="H1234",
                kwaliteit=Kwaliteit.GOED,
                habitatvoorstellen=[],
            ),
            HabitatKeuze(
                status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                habtype="H1234",
                kwaliteit=Kwaliteit.GOED,
                habitatvoorstellen=[],
            ),
        ]
    ]
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = str(test_gdf.area.iloc[0] * 0.9)
    apply_functionele_samenhang(test_gdf)
    assert test_gdf["HabitatKeuze"].iloc[0][0].habtype == "H1234"
    assert test_gdf["HabitatKeuze"].iloc[0][1].habtype == "H1234"

    # Nu dat ze samen net te weinig zijn
    test_gdf.HabitatKeuze = [
        [
            HabitatKeuze(
                status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                habtype="H1234",
                kwaliteit=Kwaliteit.GOED,
                habitatvoorstellen=[],
            ),
            HabitatKeuze(
                status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                habtype="H1234",
                kwaliteit=Kwaliteit.GOED,
                habitatvoorstellen=[],
            ),
        ]
    ]
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = str(test_gdf.area.iloc[0] * 1.1)
    apply_functionele_samenhang(test_gdf)
    assert test_gdf["HabitatKeuze"].iloc[0][0].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[0][1].habtype == "H0000"


def test_vegetatiekundig_identiek(test_gdf):
    # 2 verschillende habtypen die samen tellen voor functionele samenhang
    # Eerst met net genoeg oppervlakte
    test_gdf = test_gdf.iloc[[2]]
    test_gdf.HabitatKeuze = [
        [
            HabitatKeuze(
                status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                habtype="H2130",
                kwaliteit=Kwaliteit.GOED,
                habitatvoorstellen=[],
            ),
            HabitatKeuze(
                status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                habtype="H4030",
                kwaliteit=Kwaliteit.GOED,
                habitatvoorstellen=[],
            ),
        ]
    ]
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = str(test_gdf.area.iloc[0] * 0.9)
    os.environ[
        "VEG2HAB_FUNCTIONELE_SAMENHANG_VEGETATIEKUNDIG_IDENTIEK_RAW"
    ] = json.dumps(
        {
            "H2130": "H2130/H4030",
            "H4030": "H2130/H4030",
        }
    )
    apply_functionele_samenhang(test_gdf)
    assert test_gdf["HabitatKeuze"].iloc[0][0].habtype == "H2130"
    assert test_gdf["HabitatKeuze"].iloc[0][1].habtype == "H4030"

    # Nu met net niet genoeg oppervlakte
    test_gdf.HabitatKeuze = [
        [
            HabitatKeuze(
                status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                habtype="H2130",
                kwaliteit=Kwaliteit.GOED,
                habitatvoorstellen=[],
            ),
            HabitatKeuze(
                status=KeuzeStatus.HABITATTYPE_TOEGEKEND,
                habtype="H4030",
                kwaliteit=Kwaliteit.GOED,
                habitatvoorstellen=[],
            ),
        ]
    ]
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = str(test_gdf.area.iloc[0] * 1.1)
    apply_functionele_samenhang(test_gdf)
    assert test_gdf["HabitatKeuze"].iloc[0][0].habtype == "H0000"
    assert test_gdf["HabitatKeuze"].iloc[0][1].habtype == "H0000"
