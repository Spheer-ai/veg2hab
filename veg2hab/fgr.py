from enum import Enum
from pathlib import Path

import geopandas as gpd


class FGRType(Enum):
    DU = "Duinen"
    GG = "Getijdengebied"
    HL = "Heuvelland"
    HZ = "Hogere Zandgronden"
    LV = "Laagveengebied"
    NI = "Niet indeelbaar"
    RI = "Rivierengebied"
    ZK = "Zeekleigebied"
    AZ = "Afgesloten Zeearmen"
    NZ = "Noordzee"


class FGR:
    def __init__(self, path: Path):
        # inladen
        self.gdf = gpd.read_file(path)
        self.gdf = self.gdf[["fgr", "geometry"]]

        # omzetten naar enum (validatie)
        self.gdf["fgr"] = self.gdf["fgr"].apply(FGRType)

    # def get_fgr_for_shape(self, shape):
    #     """
    #     Geeft de FGR voor een gegeven shape
    #     """
    #     overlapping_fgr = self.gdf[self.gdf.geometry.intersects(shape)].fgr.tolist()
    #     return overlapping_fgr

    def fgr_for_geometry(self, other_gdf: gpd.GeoDataFrame):
        """
        Returns fgr codes voor de gegeven geometrie
        """
        return gpd.sjoin(other_gdf, self.gdf, how="left", predicate="within").fgr
