import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from veg2hab.mozaiek import calc_mozaiek_habtypen

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
    return gpd.GeoDataFrame(
        {
            "habtype": ["H1", "H2", "H2", "H3"],
            "ElmID": [1, 2, 3, 4],
            "mozaiek_present": [True, False, False, False],
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
        calc_mozaiek_habtypen(gdf, buffer=-0.1)


def test_warning_buffer_equals_zero(gdf):
    with pytest.warns(UserWarning):
        calc_mozaiek_habtypen(gdf, buffer=0)


def test_single_shape(gdf):
    # Enkel 1
    # NOTE: Als er niks is dan "overal" H0000???
    pre = gdf[gdf["ElmID"].isin([1])]
    post = pd.DataFrame({"H1": [100]}, index=[1])
    assert (calc_mozaiek_habtypen(pre, buffer=0) == post).all().all()


def test_two_shapes(gdf):
    # 1 en 2
    pre = gdf[gdf["ElmID"].isin([1, 2])]
    # post = {"H000": 87.5, "H2": 12.5}
    post = pd.DataFrame({"H1": [100], "H2": [12.5]}, index=[1])
    assert (calc_mozaiek_habtypen(pre, buffer=0) == post).all().all()


def test_habtype_percentage_addition(gdf):
    # 1 en 2 en 3
    pre = gdf[gdf["ElmID"].isin([1, 2, 3])]
    # post = {"H000": 75, "H2": 25}
    post = pd.DataFrame({"H1": [100], "H2": [25]}, index=[1])
    assert (calc_mozaiek_habtypen(pre, buffer=0) == post).all().all()


def test_two_habtypes(gdf):
    # 1 en 3 en 4
    pre = gdf[gdf["ElmID"].isin([1, 3, 4])]
    # post = {"H000": 75, "H2": 12.5, "H3": 12.5}
    post = pd.DataFrame({"H1": [100], "H2": [12.5], "H3": [12.5]}, index=[1])
    assert (calc_mozaiek_habtypen(pre, buffer=0) == post).all().all()


def test_all_shapes(gdf):
    # 1 en 2 en 3 en 4
    pre = gdf
    # post = {"H000": 62.5, "H2": 25, "H3": 12.5}
    post = pd.DataFrame({"H1": [100], "H2": [25], "H3": [12.5]}, index=[1])
    assert (calc_mozaiek_habtypen(pre, buffer=0) == post).all().all()


def test_multiple_mozaiek_shapes(gdf):
    # 1 en 2, beide mozaiek_present = True
    pre = gdf[gdf["ElmID"].isin([1, 2])].copy()
    pre["mozaiek_present"] = [True, True]
    post = pd.DataFrame({"H1": [100, 25], "H2": [12.5, 100]}, index=[1, 2])
    assert (calc_mozaiek_habtypen(pre, buffer=0) == post).all().all()
