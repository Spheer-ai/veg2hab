import warnings
from numbers import Number
from typing import Optional

import geopandas as gpd
from pydantic import BaseModel, PrivateAttr

from veg2hab.enums import MaybeBoolean


class Mozaiekregel(BaseModel):
    def is_mozaiek_type_present(self, type) -> bool:
        return isinstance(self, type)


class DummyMozaiekregel(Mozaiekregel):
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self) -> None:
        self._evaluation = MaybeBoolean.FALSE

    @property
    def evaluation(self) -> MaybeBoolean:
        return self._evaluation


class GeenMozaiekregel(Mozaiekregel):
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self) -> None:
        self._evaluation = MaybeBoolean.TRUE

    @property
    def evaluation(self) -> MaybeBoolean:
        return self._evaluation


def calc_mozaiek_habtypen(
    gdf: gpd.GeoDataFrame,
    buffer: Number = 0.1,
    habtype_col: str = "habtype",
    ElmID_col: str = "ElmID",
    mozaiek_present_col: str = "mozaiek_present",
) -> gpd.GeoDataFrame:
    """
    Voor alle rijen met een True in de mozaiek_present_col wordt bepaald voor hoeveel
    procent ze door elk habitattype omringd worden.
    """
    if buffer < 0:
        raise ValueError(f"Buffer moet positief zijn, maar is {buffer}")

    if buffer == 0:
        warnings.warn("Buffer is 0. Dit kan leiden tot onverwachte resultaten.")

    assert (
        mozaiek_present_col in gdf.columns
    ), f"{mozaiek_present_col} niet gevonden in gdf bij calc_mozaiek_habtypen"
    assert (
        ElmID_col in gdf.columns
    ), f"{ElmID_col} niet gevonden in gdf bij calc_mozaiek_habtypen"
    assert (
        habtype_col in gdf.columns
    ), f"{habtype_col} niet gevonden in gdf bij calc_mozaiek_habtypen"

    # Eerst trekken we een lijn om alle shapes met mozaiekregels
    buffered_boundary = gdf[gdf[mozaiek_present_col]].buffer(buffer).boundary.to_frame()
    buffered_boundary.columns = ["geometry"]
    buffered_ElmID_col = ElmID_col + "_buffered"
    buffered_boundary[buffered_ElmID_col] = gdf[ElmID_col]
    buffered_boundary["full_line_length"] = buffered_boundary.length

    # Dan leggen we alle lijnen over de originele gdf
    overlayed = gpd.overlay(buffered_boundary, gdf, how="union", keep_geom_type=True)
    overlayed["part_line_percentage"] = overlayed.length / overlayed.full_line_length

    # Dan groeperen we op ElmID en habitattype en berekenen we de som van de percentages
    summation = overlayed.pivot_table(
        values="part_line_percentage",
        index=buffered_ElmID_col,
        columns=habtype_col,
        aggfunc="sum",
        fill_value=0,
    )
    return summation * 100
