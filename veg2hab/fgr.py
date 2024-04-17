from pathlib import Path

import geopandas as gpd

from veg2hab.enums import FGRType


class FGR:
    def __init__(self, path: Path):
        # inladen
        self.gdf = gpd.read_file(path)
        self.gdf = self.gdf[["fgr", "geometry"]]

        # omzetten naar enum (validatie)
        self.gdf["fgr"] = self.gdf["fgr"].apply(FGRType)

    def fgr_for_geometry(self, other_gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
        """
        Returns fgr codes voor de gegeven geometrie
        """
        return gpd.sjoin(other_gdf, self.gdf, how="left", predicate="within").fgr
