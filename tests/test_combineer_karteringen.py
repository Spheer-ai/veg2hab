import geopandas as gpd
from shapely.geometry import Polygon

from veg2hab.vegkartering import Kartering, VegTypeInfo, _combineer_twee_geodataframes


def _is_equal(gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame) -> bool:
    # Zijn alle niet-geometry kolommen gelijk?
    if not gdf1.drop(columns="geometry").equals(gdf2.drop(columns="geometry")):
        return False

    # Zijn alle geometrieën gelijk?
    # We doen dit geometrisch ipv met equals want met equals is driehoek ABC niet gelijk aan driehoek ACB
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
    """
        +-------+           +-------+
        | 2   2 |           | 2   2 |
    +---+---+   |       +---+       |
    | 1 |1/2| 2 |  -->  | 1 | 2   2 |
    +   +---+---+       +   +---+---+
    | 1   1 |           | 1   1 |
    +-------+           +-------+
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


def test_compleet_overlappend():
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


def _make_kartering(geometry: Polygon, data_nr: int) -> Kartering:
    """
    Creeërt een dummy Kartering object met de gegeven geometrie en met data_nr als dummy data
    We zetten Area op 0 zodat we later kunnen checken of deze correct herbepaalt is
    """
    return Kartering(
        gpd.GeoDataFrame(
            {
                "ElmID": [data_nr],
                "Area": [0],
                "Datum": [data_nr],
                "Opm": [data_nr],
                "VegTypeInfo": [
                    [
                        VegTypeInfo(percentage=100, SBB=[], VvN=[]),
                    ]
                ],
                "_LokVegTyp": [data_nr],
                "_LokVrtNar": [data_nr],
                "geometry": [geometry],
            }
        )
    )


def test_combineer_karteringen():
    """
    Test ook Kartering.combineer_karteringen, niet enkel _combineer_twee_geodataframes

        +---+---+           +-------+
        |2/3| 3 |           | 3   3 |
    +---+---+---+       +---+---+   +
    | 1 |1/2|1/3|  -->  | 1 | 2 | 3 |
    +---+---+---+       +---+   +---+
        | 2 |               | 2 |
        +---+               +---+
    """
    pol1 = Polygon([(0, 1), (0, 2), (3, 2), (3, 1)])
    pol2 = Polygon([(1, 0), (1, 3), (2, 3), (2, 0)])
    pol3 = Polygon([(1, 2), (1, 3), (3, 3), (3, 1), (2, 1), (2, 2)])

    kart1 = _make_kartering(pol1, 1)
    kart2 = _make_kartering(pol2, 2)
    kart3 = _make_kartering(pol3, 3)

    # We gebruiken de Datum kolom voor vergelijken omdat "data" niet in een Kartering zit
    # Area checkt hier ook of de oppervlaktes correct herberekend worden
    expected = gpd.GeoDataFrame(
        {
            "Area": [1.0, 2.0, 3.0],
            "Datum": [1, 2, 3],
            "geometry": [
                Polygon([(0, 1), (0, 2), (1, 2), (1, 1)]),
                Polygon([(1, 0), (1, 2), (2, 2), (2, 0)]),
                Polygon([(1, 2), (1, 3), (3, 3), (3, 1), (2, 1), (2, 2)]),
            ],
        }
    )

    result = Kartering.combineer_karteringen([kart1, kart2, kart3]).gdf.drop(
        columns=["ElmID", "Opm", "VegTypeInfo", "_LokVegTyp", "_LokVrtNar"]
    )

    assert _is_equal(result, expected)
