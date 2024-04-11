import logging
import os.path
import random
import string
from typing import List

import geopandas as gpd
from typing_extensions import Self, override

from .common import InputParameters, Interface


class ArcGISInterface(Interface):
    def _generate_random_gpkg_name(self, basename: str) -> str:
        import arcpy

        file_location = os.path.abspath(os.path.join(arcpy.env.scratchWorkspace, ".."))

        random_name = f"{basename}_{''.join(random.choices(string.ascii_letters + string.digits, k=8))}.gpkg"
        return os.path.join(file_location, random_name)

    @override
    def shape_id_to_filename(self, shapefile_id: str) -> str:
        import arcpy

        filename = self._generate_random_gpkg_name("vegkart")

        gpkg_file = arcpy.management.CreateSQLiteDatabase(
            out_database_name=filename,
            spatial_type="GEOPACKAGE_1.3",
        )

        status = arcpy.conversion.FeatureClassToFeatureClass(
            in_features=shapefile_id, out_path=gpkg_file, out_name="main"
        )

        if status.status != 4:
            raise RuntimeError(f"Failed to convert shapefile to GeoPackage: {status}")

        return gpkg_file

    def output_shapefile(self, shapefile_id: str, gdf: gpd.GeoDataFrame) -> None:
        # TODO use shapefile_id as output
        import arcpy

        filename = self._generate_random_gpkg_name("habkart")

        gdf.to_file(filename, driver="GPKG", layer="main")

        arcpy.MakeFeatureLayer_management(
            in_features=filename + "/main",
            out_layer=os.path.splitext(os.path.basename(filename))[0],
        )

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
