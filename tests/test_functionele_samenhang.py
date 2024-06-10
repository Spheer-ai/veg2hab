import json
import os

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from veg2hab.enums import KeuzeStatus, Kwaliteit
from veg2hab.functionele_samenhang import (
    _cluster_vlakken,
    _UnionFind,
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
    # We zetten hier meteen de env variables weer even goed voor als deze test uitgevoerd wordt na test_env_vars_overwrite_config
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
                ][
                    VegTypeInfo(SBB=[], VvN=[], percentage=90),
                    VegTypeInfo(SBB=[], VvN=[], percentage=10),
                ][
                    VegTypeInfo(SBB=[], VvN=[], percentage=90),
                    VegTypeInfo(SBB=[], VvN=[], percentage=10),
                ],
            ],
            "HabitatKeuze": [
                [HabitatKeuze(KeuzeStatus.DUIDELIJK, "H1234", Kwaliteit.GOED, [])],
                [HabitatKeuze(KeuzeStatus.DUIDELIJK, "H1234", Kwaliteit.GOED, [])],
                [
                    HabitatKeuze(KeuzeStatus.DUIDELIJK, "H1234", Kwaliteit.GOED, []),
                    HabitatKeuze(KeuzeStatus.DUIDELIJK, "H4321", Kwaliteit.GOED, []),
                ],
                [
                    HabitatKeuze(KeuzeStatus.DUIDELIJK, "H1234", Kwaliteit.GOED, []),
                    HabitatKeuze(KeuzeStatus.DUIDELIJK, "H4321", Kwaliteit.GOED, []),
                ],
                [
                    HabitatKeuze(KeuzeStatus.DUIDELIJK, "H1234", Kwaliteit.GOED, []),
                    HabitatKeuze(KeuzeStatus.DUIDELIJK, "H4321", Kwaliteit.GOED, []),
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


def test_UnionFind_clustering():
    clusters = [[1, 2, 3], [2, 4], [5]]
    assert compare_clusterings(_UnionFind.cluster_lists(clusters), [[1, 2, 3, 4], [5]])

    clusters = [[1, 2], [3, 4], [5, 6], [2, 3]]
    assert compare_clusterings(
        _UnionFind.cluster_lists(clusters), [[1, 2, 3, 4], [5, 6]]
    )

    clusters = [[1, 2], [2, 3], [4, 5], [1, 6], [4, 7, 8], [10, 10]]
    assert compare_clusterings(
        _UnionFind.cluster_lists(clusters), [[1, 2, 3, 6], [4, 5, 7, 8], [10]]
    )


def test_functionele_samenhang_clustering_base_case(test_gdf):
    # normal case
    clustered = _cluster_vlakken(test_gdf)
    assert compare_clusterings(clustered, [[1, 2, 3, 4, 5]])


def test_functionele_samenhang_clustering_multiple_clusters(test_gdf):
    # test with 2 clusters (remove ElmID 4)
    test_gdf = test_gdf.drop(3)
    clustered = _cluster_vlakken(test_gdf)
    assert compare_clusterings(clustered, [[1, 2, 3], [5]])

    # test with 3 clusters (change buffer distances)
    os.environ["VEG2HAB_FUNCTIONELE_SAMENHANG_BUFFER_DISTANCES"] = json.dumps(
        [
            (100, 100, 0.01),
            (90, 100, 0.01),
            (50, 90, 0.01),
        ]
    )
