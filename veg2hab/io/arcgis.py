from textwrap import dedent
from pathlib import Path
from pkg_resources import resource_filename
from typing_extensions import Literal

from pydantic import BaseModel, Field
from pydantic.fields import ModelField
import logging
import geopandas as gpd

from .common import Interface

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
            handlers=[ArcpyAddMessageHandler()]
        )

    def get_parameter_class(self):
        # TODO
        pass



# TODO move a basemodel into a common folder
# and make a specific arcgis / qgis model
class Parameters(BaseModel):
    """ TODO i want these arcgis specific stuff into its own file """
    shapefile: str = Field(
        description="Path to the shapefile",
    )
    ElmID_col: str = Field(
        description="De kolomnaam van de ElementID in de Shapefile; uniek per vlak",
    )
    vegtype_col_format: Literal["single", "multi"] = Field(
        description='"single" als complexen in 1 kolom zitten of "multi" als er meerdere kolommen zijn',
    )


    @classmethod
    def from_parameter_list(cls, parameters):
        as_dict = {p.name: p.valueAsText for p in parameters}
        return cls(**as_dict)

    @classmethod
    def to_parameter_list(cls):
        # import arcpy

        outputs = []
        for field_name, field_info in cls.__fields__.items():

            outputs.append(
                # arcpy.Parameter
                dict(
                    name=field_name,
                    displayName=field_info.description,
                    datatype="Field",
                    parameterType="Required",
                    direction="Input"
                )
            )
