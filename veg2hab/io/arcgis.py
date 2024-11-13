import logging
import os.path
import random
import string
import tempfile
import time
from pathlib import Path
from typing import List, Optional

import geopandas as gpd
from typing_extensions import Self, override

from .. import enums
from .common import (
    AccessDBInputs,
    ApplyDefTabelInputs,
    ApplyFunctioneleSamenhangInputs,
    ApplyMozaiekInputs,
    Interface,
    OverrideCriteriumIO,
    ShapefileInputs,
    StackVegKarteringInputs,
)

MAX_N_OVERRIDE = 50  # NOTE: we this results in max 49 overrides, since we start at 1


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

        filename = self._generate_random_gpkg_name("kaart")

        gpkg_file = arcpy.management.CreateSQLiteDatabase(
            out_database_name=filename,
            spatial_type="GEOPACKAGE_1.3",
        )

        status = arcpy.conversion.FeatureClassToFeatureClass(
            in_features=shapefile_id, out_path=gpkg_file, out_name="main"
        )

        time.sleep(0.5)  # screw you ArcGIS!

        if status.status != 4:
            raise RuntimeError(f"Failed to convert shapefile to GeoPackage: {status}")

        return Path(filename)

    @override
    def output_shapefile(
        self, shapefile_id: Optional[Path], gdf: gpd.GeoDataFrame
    ) -> None:
        import arcpy

        if shapefile_id is None:
            filename = self._generate_random_gpkg_name("kaart")
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


def _override_mits_params() -> List["arcpy.Parameter"]:
    import arcpy

    enable = True
    return_value = []
    for idx in range(1, MAX_N_OVERRIDE):
        param1 = arcpy.Parameter(
            name=f"override_{idx}_mits",
            displayName=f"Handmatig te overschrijven mits {idx}",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        param1.filter.type = "ValueList"
        param1.filter.list = [
            " "
        ] + enums.STR_MITSEN  # we use an empty string to deselect the value
        param1.enabled = enable
        # just enable the first mits for the first one.
        enable = False

        param2 = arcpy.Parameter(
            name=f"override_{idx}_truth_value",
            displayName=f"Waarde die geldt voor mits {idx}",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        param2.filter.type = "ValueList"
        param2.filter.list = ["WAAR", "ONWAAR", "ONDUIDELIJK"]
        param2.enabled = enable

        param3 = arcpy.Parameter(
            name=f"override_{idx}_geometry",
            displayName=f"Geometrie waarbinnen mits {idx} deze waarde krijgt, als niet gegeven geldt dit voor de hele kartering",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
        )
        param3.enabled = enable

        param4 = arcpy.Parameter(
            name=f"override_{idx}_truth_value_outside",
            displayName=f"Waarde die geldt voor mits {idx} buiten geometrie, alleen van toepassing als geometrie gegeven is",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        param4.filter.type = "ValueList"
        param4.filter.list = ["WAAR", "ONWAAR", "ONDUIDELIJK"]
        param4.enabled = enable

        return_value.extend([param1, param2, param3, param4])
    return return_value


def _schema_to_param_list(param_schema: dict) -> List["arcpy.Parameter"]:
    import arcpy

    outputs = []
    for field_name, field_info in param_schema["properties"].items():
        if field_name == "override_dict":
            param_group = _override_mits_params()
            outputs.extend(param_group)
            continue
        elif field_name == "shapefile":
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
            direction="Output" if field_name == "output" else "Input",
            multiValue=field_info.get("type") == "array",
        )

        if field_name == "shapefile":
            shapefile_param = param

        if field_name == "access_mdb_path":
            param.filter.list = ["mdb", "accdb"]

        if field_name == "output":
            param.filter.list = ["gpkg"]

        if "enum" in field_info.keys():
            param.filter.type = "ValueList"
            param.filter.list = field_info["enum"]
        elif field_name == "welke_typologie":
            param.filter.type = "ValueList"
            ref_name = field_info.get("allOf")[0].get("$ref").split("/")[-1]
            param.filter.list = param_schema["definitions"][ref_name]["enum"]

        outputs.append(param)

    for param in outputs:
        if param.name.endswith("_col"):
            param.parameterDependencies = [shapefile_param.name]

    return outputs


class ArcGISMixin:
    """mixin for arcgis classes"""

    @classmethod
    def from_parameter_list(cls, parameters: List["arcpy.Parameter"]) -> Self:
        params_dict = {p.name: p.valueAsText for p in parameters}
        return cls(**params_dict)

    @classmethod
    def to_parameter_list(cls) -> List["arcpy.Parameter"]:
        return _schema_to_param_list(cls.schema())

    @classmethod
    def update_parameters(cls, parameters: List["arcpy.Parameter"]) -> None:
        pass


class ArcGISAccessDBInputs(AccessDBInputs, ArcGISMixin):
    pass


class ArcGISShapefileInputs(ShapefileInputs, ArcGISMixin):
    @classmethod
    def from_parameter_list(cls, parameters: List["arcpy.Parameter"]) -> Self:
        params_dict = {p.name: p.valueAsText for p in parameters}
        for col in ["sbb_col", "vvn_col", "rvvn_col", "perc_col", "lok_vegtypen_col"]:
            if params_dict.get(col) is None:
                params_dict[col] = []
            else:
                params_dict[col] = params_dict[col].split(";")

        return cls(**params_dict)

    @classmethod
    def update_parameters(cls, parameters: List["arcpy.Parameter"]) -> None:
        params_dict = {p.name: p for p in parameters}
        if params_dict["vegtype_col_format"].altered:
            is_multivalue_per_column = (
                params_dict["vegtype_col_format"].valueAsText == "single"
            )
            params_dict["split_char"].enabled = is_multivalue_per_column

            # NOTE: doet nu niks, maar als ze dit fixen/implementeren zou de interface mooier moeten zijn
            params_dict["sbb_col"].multiValue = not is_multivalue_per_column
            params_dict["vvn_col"].multiValue = not is_multivalue_per_column
            params_dict["perc_col"].multiValue = not is_multivalue_per_column
            params_dict["lok_vegtypen_col"].multiValue = not is_multivalue_per_column

        if params_dict["welke_typologie"].altered:
            params_dict["rvvn_col"].enabled = (
                params_dict["welke_typologie"].valueAsText == "rVvN"
            )
            params_dict["sbb_col"].enabled = params_dict[
                "welke_typologie"
            ].valueAsText in {
                "SBB",
                "SBB en VvN",
            }
            params_dict["vvn_col"].enabled = params_dict[
                "welke_typologie"
            ].valueAsText in {
                "VvN",
                "SBB en VvN",
            }


class ArcGISStackVegKarteringInputs(StackVegKarteringInputs, ArcGISMixin):
    @classmethod
    def from_parameter_list(cls, parameters: List["arcpy.Parameter"]) -> Self:
        params_dict = {p.name: p.valueAsText for p in parameters}
        col = "shapefile"
        if params_dict.get(col) is None:
            params_dict[col] = []
        else:
            params_dict[col] = params_dict[col].split(";")

        return cls(**params_dict)


class ArcGISApplyDefTabelInputs(ApplyDefTabelInputs, ArcGISMixin):
    @staticmethod
    def _is_override_empty(self, param_value: Optional[str]) -> bool:
        return (param_value is None) or (param_value == " ")

    @classmethod
    def from_parameter_list(cls, parameters: List["arcpy.Parameter"]) -> Self:
        params_dict = {p.name: p.valueAsText for p in parameters}

        override_dict = []
        for i in range(1, MAX_N_OVERRIDE):
            if not cls._is_override_empty(params_dict.get(f"override_{i}_mits")):
                override_dict.append(
                    OverrideCriteriumIO(
                        mits=params_dict[f"override_{i}_mits"],
                        truth_value=params_dict[f"override_{i}_truth_value"],
                        override_geometry=params_dict[f"override_{i}_geometry"],
                        truth_value_outside=params_dict[
                            f"override_{i}_truth_value_outside"
                        ],
                    )
                )

        filtered_dict = {
            k: v for k, v in params_dict.items() if not k.startswith("override_")
        }
        filtered_dict["override_dict"] = override_dict

        return cls(**filtered_dict)

    @classmethod
    def update_parameters(cls, parameters: List["arcpy.Parameter"]) -> None:
        params_dict = {p.name: p for p in parameters}

        for idx in range(1, MAX_N_OVERRIDE):
            is_override_set = not cls._is_override_empty(
                params_dict[f"override_{idx}_mits"].valueAsText
            )

            if idx != (MAX_N_OVERRIDE - 1):
                params_dict[f"override_{idx + 1}_mits"].enabled = is_override_set

            params_dict[f"override_{idx}_truth_value"].enabled = is_override_set
            params_dict[f"override_{idx}_geometry"].enabled = is_override_set
            params_dict[f"override_{idx}_truth_value_outside"].enabled = is_override_set

            if not is_override_set:
                params_dict[f"override_{idx}_truth_value"].value = None
                params_dict[f"override_{idx}_geometry"].value = None
                params_dict[f"override_{idx}_truth_value_outside"].value = None

        # shift override criteria down, if one of 'm not set properly
        idx = 0
        while idx < (MAX_N_OVERRIDE - 1):
            if cls._is_override_empty(
                params_dict[f"override_{idx}_mits"].valueAsText
            ) and not cls._is_override_empty(
                params_dict[f"override_{idx + 1}_mits"].valueAsText
            ):
                # shift all the values over 1
                params_dict[f"override_{idx}_mits"].value = params_dict[
                    f"override_{idx + 1}_mits"
                ].value
                params_dict[f"override_{idx}_truth_value"].value = params_dict[
                    f"override_{idx + 1}_truth_value"
                ].value
                params_dict[f"override_{idx}_geometry"].value = params_dict[
                    f"override_{idx + 1}_geometry"
                ].value
                params_dict[f"override_{idx}_truth_value_outside"].value = params_dict[
                    f"override_{idx + 1}_truth_value_outside"
                ].value

                params_dict[f"override_{idx + 1}_mits"].value = None
                params_dict[f"override_{idx + 1}_truth_value"].value = None
                params_dict[f"override_{idx + 1}_geometry"].value = None
                params_dict[f"override_{idx + 1}_truth_value_outside"].value = None

            else:
                idx += 1


class ArcGISApplyMozaiekInputs(ApplyMozaiekInputs, ArcGISMixin):
    pass


class ArcGISApplyFunctioneleSamenhangInputs(
    ApplyFunctioneleSamenhangInputs, ArcGISMixin
):
    pass
