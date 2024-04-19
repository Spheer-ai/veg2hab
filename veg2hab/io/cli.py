import logging

from geopandas.geodataframe import GeoDataFrame
from typing_extensions import override

from .common import AccessDBInputs, Interface, ShapefileInputs


class CLIInterface(Interface):
    @override
    def output_shapefile(self, shapefile_id: str, gdf: GeoDataFrame) -> None:
        gdf.to_file(shapefile_id, driver="GPKG", layer="main")

    @override
    def instantiate_loggers(self) -> None:
        logging.basicConfig(level=logging.INFO)
