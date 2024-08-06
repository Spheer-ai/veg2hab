import geopandas as gpd
from shapely.geometry import Polygon

from veg2hab.vegkartering import (
    Kartering,
    _combineer_twee_geodataframes,
    combineer_karteringen,
)


def _is_equal(gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame) -> bool:
    if not gdf1.drop(columns="geometry").equals(gdf2.drop(columns="geometry")):
        return False
    
    return gdf1.symmetric_difference(gdf2).is_empty.all()


def test_geen_overlap():
    """
    +---+    +---+       +---+    +---+
    | 1 |    | 2 |  -->  | 1 |    | 2 |
    +---+    +---+       +---+    +---+    
    """
    # Geen overlap
    gdf1 = gpd.GeoDataFrame(
        {
            "data": [1],
            "geometry": [Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])],
        }
    )
    gdf2 = gpd.GeoDataFrame(
        {
            "data": [2],
            "geometry": [Polygon([(2, 0), (2, 1), (3, 1), (3, 0)])],
        }
    )

    expected = gpd.GeoDataFrame(
        {
            "data": [
                1,
                2,
            ],
            "geometry": [
                Polygon([(0, 0), (0, 1), (1, 1), (1, 0)]),
                Polygon([(2, 0), (2, 1), (3, 1), (3, 0)]),
            ],
        }
    )

    result = _combineer_twee_geodataframes(gdf1, gdf2)

    assert _is_equal(result, expected)

def test_grenzend():
    """
    +---+---+       +---+---+
    | 1 | 2 |  -->  | 1 | 2 |
    +---+---+       +---+---+
    """
    # Grenzend
    gdf1 = gpd.GeoDataFrame(
        {
            "data": [1],
            "geometry": [Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])],
        }
    )
    gdf2 = gpd.GeoDataFrame(
        {
            "data": [2],
            "geometry": [Polygon([(1, 0), (1, 1), (2, 1), (2, 0)])],
        }
    )

    expected = gpd.GeoDataFrame(
        {
            "data": [
                1,
                2,
            ],
            "geometry": [
                Polygon([(0, 0), (0, 1), (1, 1), (1, 0)]),
                Polygon([(1, 0), (1, 1), (2, 1), (2, 0)]),
            ],
        }
    )

    result = _combineer_twee_geodataframes(gdf1, gdf2)

    assert _is_equal(result, expected)

def test_overlappend():
    """  ______          ______
        |  2  |         |  2  |
    +---+--+  |     +---+     |
    | 1 |__|__| --> | 1 |__ __|
    |      |        |      |
    +------+        +------+
    """
    # Overlappend
    gdf1 = gpd.GeoDataFrame(
        {
            "data": [1],
            "geometry": [Polygon([(0, 0), (0, 2), (2, 2), (2, 0)])],
        }
    )
    gdf2 = gpd.GeoDataFrame(
        {
            "data": [2],
            "geometry": [Polygon([(1, 1), (1, 3), (3, 3), (3, 1)])],
        }
    )

    expected = gpd.GeoDataFrame(
        {
            "data": [
                1,
                2,
            ],
            "geometry": [
                Polygon([(0, 0), (0, 2), (1, 2), (1, 1), (2, 1), (2, 0)]),
                Polygon([(1, 1), (1, 3), (3, 3), (3, 1)]),
            ],
        }
    )

    result = _combineer_twee_geodataframes(gdf1, gdf2)

    assert _is_equal(result, expected)


def test_splittend():
    """
        +---+               +---+
        | 2 |               | 2 |
    +---+---+---+       +---+   +---+
    | 1 |1/2| 1 |  -->  | 1 | 2 | 1 |
    +---+---+---+       +---+   +---+
        | 2 |               | 2 |
        +---+               +---+
    """
    gdf1 = gpd.GeoDataFrame(
        {
            "data": [1],
            "geometry": [Polygon([(0, 1), (0, 2), (3, 2), (3, 1)])],
        }
    )
    gdf2 = gpd.GeoDataFrame(
        {
            "data": [2],
            "geometry": [Polygon([(1, 0), (1, 3), (2, 3), (2, 0)])],
        }
    )

    expected = gpd.GeoDataFrame(
        {
            "data": [
                1,
                1,
                2,
            ],
            "geometry": [
                Polygon([(2, 1), (2, 2), (3, 2), (3, 1)]),
                Polygon([(0, 1), (0, 2), (1, 2), (1, 1)]),
                Polygon([(1, 0), (1, 3), (2, 3), (2, 0)]),
            ],
        }
    )

    result = _combineer_twee_geodataframes(gdf1, gdf2)

    assert _is_equal(result, expected)


def test_complete_overlap():
    """
    +-----------+       +-----------+
    |  2     2  |       |  2     2  |
    |   +---+   |       |           |
    |   | 1 |   |  -->  |     2     |
    |   +---+   |       |           |
    |  2     2  |       |  2     2  |
    +-----------+       +-----------+
    """
    gdf1 = gpd.GeoDataFrame(
        {
            "data": [1],
            "geometry": [Polygon([(1, 1), (1, 2), (2, 2), (2, 1)])],
        }
    )
    gdf2 = gpd.GeoDataFrame(
        {
            "data": [2],
            "geometry": [Polygon([(0, 0), (0, 3), (3, 3), (3, 0)])],
        }
    )

    expected = gpd.GeoDataFrame(
        {
            "data": [
                2,
            ],
            "geometry": [
                Polygon([(0, 0), (0, 3), (3, 3), (3, 0)]),
            ],
        }
    )

    result = _combineer_twee_geodataframes(gdf1, gdf2)

    assert _is_equal(result, expected)
