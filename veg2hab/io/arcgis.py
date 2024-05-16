import logging
import os.path
import random
import string
import tempfile
from pathlib import Path
from typing import List, Optional

import geopandas as gpd
from pydantic import validator
from typing_extensions import Self, override

from .common import AccessDBInputs, Interface, ShapefileInputs


class ArcGISInterface(Interface):
    def _get_temp_dir(self):
        import arcpy

        if arcpy.env.scratchWorkspace is not None:
            return os.path.abspath(os.path.join(arcpy.env.scratchWorkspace, ".."))
        if arcpy.env.scratchFolder is not None:
            return arcpy.env.scratchFolder

        return tempfile.gettempdir()

    def _generate_random_gpkg_name(self, basename: str) -> str:
        import arcpy

        random_name = f"{basename}_{''.join(random.choices(string.ascii_letters + string.digits, k=8))}.gpkg"
        return os.path.join(self._get_temp_dir(), random_name)

    @override
    def shape_id_to_filename(self, shapefile_id: str) -> Path:
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

        return Path(filename)

    @override
    def output_shapefile(
        self, shapefile_id: Optional[Path], gdf: gpd.GeoDataFrame
    ) -> None:
        # TODO use shapefile_id as output
        import arcpy

        if shapefile_id is None:
            filename = self._generate_random_gpkg_name("habkart")
        else:
            filename = str(shapefile_id)

        gdf.to_file(filename, driver="GPKG", layer="main")

        logging.info(f"Output is weggeschreven naar {filename}")

        try:
            result = arcpy.MakeFeatureLayer_management(
                in_features=filename + "/main",
                out_layer=os.path.splitext(os.path.basename(filename))[0],
            )
            layer = result.getOutput(0)
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            aprx.activeMap.addLayer(layer)
        except Exception as e:
            logging.warning(
                f"Kon de output niet toevoegen aan de kaart. Lees deze handmatig in vanaf {filename}"
            )
            logging.error(str(e))

    @override
    def instantiate_loggers(self, log_level: int = logging.INFO) -> None:
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
            level=log_level,
            handlers=[ArcpyAddMessageHandler()],
        )


def _schema_to_param_list(param_schema: dict) -> List["arcpy.Parameter"]:
    import arcpy

    outputs = []
    for field_name, field_info in param_schema["properties"].items():
        if field_name == "shapefile":
            datatype = "GPFeatureLayer"
        elif field_name.endswith("_col"):
            datatype = "Field"
        elif field_info.get("format", "") == "path":
            datatype = "DEFile"
        else:
            datatype = "GPString"

        is_required = field_name in param_schema["required"]

        # get the description from the field
        param = arcpy.Parameter(
            name=field_name,
            displayName=field_info["description"],
            datatype=datatype,
            parameterType="Required" if is_required else "Optional",
            direction="Input",
            multiValue=field_info.get("type") == "array",
        )

        if field_name == "shapefile":
            shapefile_param = param

        if field_name == "access_mdb_path":
            param.filter.list = ["mdb", "accdb"]

        if "enum" in field_info.keys():
            param.filter.type = "ValueList"
            param.filter.list = field_info["enum"]

        outputs.append(param)

    for param in outputs:
        if param.name.endswith("_col"):
            param.parameterDependencies = [shapefile_param.name]

    return outputs


class ArcGISAccessDBInputs(AccessDBInputs):
    @classmethod
    def from_parameter_list(cls, parameters: List["arcpy.Parameter"]) -> Self:
        as_dict = {p.name: p.valueAsText for p in parameters}
        return cls(**as_dict)

    @classmethod
    def to_parameter_list(cls) -> List["arcpy.Parameter"]:
        return _schema_to_param_list(cls.schema())

    @classmethod
    def update_parameters(cls, parameters: List["arcpy.Parameter"]) -> None:
        as_dict = {p.name: p for p in parameters}
        if as_dict["vegtype_col_format"].altered:
            is_multivalue_per_column = (
                as_dict["vegtype_col_format"].valueAsText == "single"
            )
            as_dict["split_char"].enabled = is_multivalue_per_column

        if as_dict["sbb_of_vvn"].altered:
            as_dict["sbb_col"].enabled = as_dict["sbb_of_vvn"].valueAsText != "VvN"
            as_dict["vvn_col"].enabled = as_dict["sbb_of_vvn"].valueAsText != "SBB"


class ArcGISShapefileInputs(ShapefileInputs):
    @classmethod
    def from_parameter_list(cls, parameters: List["arcpy.Parameter"]) -> Self:
        as_dict = {p.name: p.valueAsText for p in parameters}
        return cls(**as_dict)

    @classmethod
    def to_parameter_list(cls) -> List["arcpy.Parameter"]:
        return _schema_to_param_list(cls.schema())

    @classmethod
    def update_parameters(cls, parameters: List["arcpy.Parameter"]) -> None:
        pass

    @validator("sbb_col", "vvn_col", "perc_col", "lok_vegtypen_col", pre=True)
    def allow_none_and_strings(cls, v: List[Optional[str]]) -> List[List[str]]:
        return [col.split(";") if col is not None else [] for col in v]
