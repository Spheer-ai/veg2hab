from abc import ABCMeta, abstractmethod
from typing import Type, ClassVar

from typing_extensions import Self

import geopandas as gpd
from pydantic import BaseModel

class Parameters(BaseModel):
    pass


class Interface(metaclass=ABCMeta):
    __instance = None

    # make the constructor private
    def __new__(cls):
        raise TypeError("Interface is a singleton class and cannot only be accessed through get_instance")

    @classmethod
    def get_instance(cls) -> Self:
        if Interface.__instance is None:
            Interface.__instance = object.__new__(cls)
        return Interface.__instance

    @abstractmethod
    def read_shapefile(self, shapefile_id: str) -> gpd.GeoDataFrame:
        """Read the shapefile with the given id."""

    @abstractmethod
    def output_shapefile(self, shapefile_id: str, gdf: gpd.GeoDataFrame) -> None:
        """Output the shapefile with the given id.
        ID would either be a path to a shapefile or an identifier to a shapefile in ArcGIS or QGIS.
        """

    @abstractmethod
    def instantiate_loggers(self) -> None:
        """Instantiate the loggers for the module."""

    @abstractmethod
    def get_parameter_class(self) -> Type[Parameters]:
        """Get the class that holds the parameters the main function"""
