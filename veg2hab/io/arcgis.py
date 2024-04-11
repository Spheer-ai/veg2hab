import logging
from typing import List

import geopandas as gpd
from typing_extensions import Self

from .common import InputParameters, Interface


class ArcGISInterface(Interface):
    def read_shapefile(self, shapefile_id: str) -> gpd.GeoDataFrame:
        # TODO
        pass

    def output_shapefile(self, shapefile_id: str, gdf: gpd.GeoDataFrame) -> None:
        # TODO
        pass

    def instantiate_loggers(self) -> None:
        """Instantiate the loggers for the module."""

        class ArcpyAddMessageHandler(logging.Handler):
            def emit(self, record: logging.LogRecord):
                import arcpy

                msg = self.format(record)
                if record.levelno >= logging.ERROR:
                    arcpy.AddError(msg)
                elif record.levelno >= logging.WARNING:
                    arcpy.AddWarning(msg)
                else:
                    # this will map debug into info, but that's just
                    # the way it is now..
                    arcpy.AddMessage(msg)

        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO,
            handlers=[ArcpyAddMessageHandler()],
        )

    def get_parameter_class(self):
        # TODO is this really neccesary?
        pass


class ArcGISParameters(InputParameters):
    @classmethod
    def from_parameter_list(cls, parameters: List["arcpy.Parameter"]) -> Self:
        as_dict = {p.name: p.valueAsText for p in parameters}
        return cls(**as_dict)

    @classmethod
    def to_parameter_list(cls) -> List["arcpy.Parameter"]:
        import arcpy

        outputs = []
        for field_name, field_info in cls.schema()["properties"].items():
            if field_name == "shapefile":
                datatype = "GPFeatureLayer"
            elif field_name.endswith("_col"):
                datatype = "Field"
            else:
                datatype = "GPString"

            # get the description from the field
            param = arcpy.Parameter(
                name=field_name,
                displayName=field_info["description"],
                datatype=datatype,
                parameterType="Required",
                direction="Input",
            )

            if "enum" in field_info.keys():
                param.filter.type = "ValueList"
                param.filter.list = field_info["enum"]

            outputs.append(param)
        return outputs
