from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import ClassVar, Optional, Type

import geopandas as gpd
from pydantic import BaseModel, Field
from typing_extensions import Literal, Self


class AccessDBInputs(BaseModel):
    label: ClassVar[str] = "digitale_standaard"
    description: ClassVar[str] = "Draai veg2hab o.b.v. de digitale standaard"
    shapefile: str = Field(
        description="Locatie van de vegetatiekartering",
    )
    ElmID_col: str = Field(
        description="De kolomnaam van de ElementID in de Shapefile; deze wordt gematched aan de Element tabel in de AccessDB",
    )
    access_mdb_path: Path = Field(
        description="Locatie van de .mdb file van de digitale standaard",
    )
    opmerkingen_column: Optional[str] = Field(
        default=None, description="kolomnaam van de opmerking als deze er is"
    )
    datum_column: Optional[str] = Field(
        default=None, description="kolomnaam van de datum als deze er is"
    )


class ShapefileInputs(BaseModel):
    label: ClassVar[str] = "vector_bestand"
    description: ClassVar[str] = "Draai veg2hab o.b.v. een vector bestand"
    shapefile: str = Field(
        description="Locatie van de vegetatiekartering",
    )
    ElmID_col: str = Field(
        description="De kolomnaam van de ElementID in de Shapefile; uniek per vlak",
    )
    vegtype_col_format: Literal["single", "multi"] = Field(
        description='"single" als complexen in 1 kolom zitten of "multi" als er meerdere kolommen zijn',
    )
    sbb_of_vvn: Literal["VvN", "SBB", "beide"] = Field(
        description='"VvN" als VvN de voorname vertaling is vanuit het lokale type, "SBB" voor SBB en "beide" als beide er zijn.'
    )
    datum_col: Optional[str] = Field(
        default=None, description="kolomnaam van de datum als deze er is"
    )
    opmerking_col: Optional[str] = Field(
        default=None, description="kolomnaam van de opmerking als deze er is"
    )
    SBB_col: Optional[str] = Field(
        default=None,
        description="kolomnaam van de SBB vegetatietypen als deze er is (bij multi_col: alle kolomnamen gesplitst door vegtype_split_char)",
    )
    VvN_col: Optional[str] = Field(
        default=None,
        description="kolomnaam van de VvN vegetatietypen als deze er is (bij multi_col: alle kolomnamen gesplitst door vegtype_split_char)",
    )
    split_char: Optional[str] = Field(
        default="+",
        description='karakter waarop de vegetatietypen gesplitst moeten worden (voor complexen (bv "16aa2+15aa")) (wordt bij mutli_col gebruikt om de kolommen te scheiden)',
    )
    perc_col: Optional[str] = Field(
        default=None,
        description="kolomnaam van de percentage als deze er is (bij multi_col: alle kolomnamen gesplitst door vegtype_split_char))",
    )


class Interface(metaclass=ABCMeta):
    """Singleton class that defines the interface for the different UI systems."""

    __instance = None

    # make the constructor private
    def __new__(cls):
        raise TypeError(
            "Interface is a singleton class and cannot only be accessed through get_instance"
        )

    @classmethod
    def get_instance(cls) -> Self:
        if Interface.__instance is None:
            Interface.__instance = object.__new__(cls)
        return Interface.__instance

    def shape_id_to_filename(self, shapefile_id: str) -> str:
        """Convert the shapefile id to a (temporary) file and returns the filename"""
        return shapefile_id

    @abstractmethod
    def output_shapefile(self, shapefile_id: str, gdf: gpd.GeoDataFrame) -> None:
        """Output the shapefile with the given id.
        ID would either be a path to a shapefile or an identifier to a shapefile in ArcGIS or QGIS.
        """

    @abstractmethod
    def instantiate_loggers(self) -> None:
        """Instantiate the loggers for the module."""
