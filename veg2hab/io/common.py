from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import ClassVar, Optional

import geopandas as gpd
from pydantic import BaseModel, BaseSettings, Field
from typing_extensions import List, Literal, Union


class AccessDBInputs(BaseModel):
    class Config:
        extra = "forbid"

    label: ClassVar[str] = "digitale_standaard"
    description: ClassVar[str] = "Draai veg2hab o.b.v. de digitale standaard"
    shapefile: str = Field(
        description="Locatie van de vegetatiekartering",
    )
    elmid_col: str = Field(
        description="De kolomnaam van de ElementID in de Shapefile; deze wordt gematched aan de Element tabel in de AccessDB",
    )
    access_mdb_path: Path = Field(
        description="Locatie van de .mdb file van de digitale standaard",
    )
    datum_col: Optional[str] = Field(
        default=None,
        description="Datum kolom (optioneel), deze wordt onveranderd aan de output meegegeven",
    )
    opmerking_col: Optional[str] = Field(
        default=None,
        description="Opmerking kolom (optioneel), deze wordt onveranderd aan de output meegegeven",
    )
    output: Optional[Path] = Field(
        default=None,
        description="Output bestand (optioneel), indien niet gegeven wordt er een bestandsnaam gegenereerd",
    )


class ShapefileInputs(BaseModel):
    class Config:
        extra = "forbid"

    label: ClassVar[str] = "vector_bestand"
    description: ClassVar[str] = "Draai veg2hab o.b.v. een vector bestand"
    shapefile: str = Field(
        description="Locatie van de vegetatiekartering",
    )
    vegtype_col_format: Literal["single", "multi"] = Field(
        description='"single" als complexen in 1 kolom zitten of "multi" als er meerdere kolommen zijn',
    )
    sbb_of_vvn: Literal["VvN", "SBB", "beide"] = Field(
        description='"VvN" als VvN de voorname vertaling is vanuit het lokale type, "SBB" voor SBB en "beide" als beide er zijn.'
    )
    elmid_col: Optional[str] = Field(
        description="De kolomnaam van de ElementID in de Shapefile; uniek per vlak",
    )
    datum_col: Optional[str] = Field(
        default=None,
        description="Datum kolom (optioneel), deze wordt onveranderd aan de output meegegeven",
    )
    opmerking_col: Optional[str] = Field(
        default=None,
        description="Opmerking kolom (optioneel), deze wordt onveranderd aan de output meegegeven",
    )
    sbb_col: Optional[str] = Field(
        default=None,
        description="kolomnaam van de SBB vegetatietypen als deze er is (bij multi_col: alle kolomnamen gesplitst door vegtype_split_char)",
    )
    vvn_col: Optional[str] = Field(
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
    lok_vegtypen_col: Optional[str] = Field(
        default=None,
        description="kolomnaam van de lokale vegetatietypen als deze er is (bij multi_col: alle kolomnamen gesplitst door vegtype_split_char))",
    )
    output: Optional[Path] = Field(
        default=None,
        description="Output bestand (optioneel), indien niet gegeven wordt er een bestandsnaam gegenereerd",
    )


class Veg2HabConfig(BaseSettings):
    class Config:
        env_prefix = "VEG2HAB_"

    mozaiek_threshold: Union[int, float] = Field(
        default=95.0,
        description="Threshold voor het bepalen of een vlak in het mozaiek ligt",
    )
    mozaiek_als_rand_threshold: Union[int, float] = Field(
        default=50.0,
        description="Threshold voor het bepalen of een vlak langs de rand van het mozaiek ligt",
    )
    niet_geautomatiseerde_sbb: List[str] = Field(
        default=[
            "100",
            "200",
            "300",
            "400",
        ],
        description="SBB vegetatietypen die niet geautomatiseerd kunnen worden",
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
    def get_instance(cls):
        if Interface.__instance is None:
            Interface.__instance = object.__new__(cls)
        return Interface.__instance

    def shape_id_to_filename(self, shapefile_id: str) -> Path:
        """Convert the shapefile id to a (temporary) file and returns the filename"""
        return Path(shapefile_id)

    @abstractmethod
    def output_shapefile(
        self, shapefile_id: Optional[Path], gdf: gpd.GeoDataFrame
    ) -> None:
        """Output the shapefile with the given id.
        ID would either be a path to a shapefile or an identifier to a shapefile in ArcGIS or QGIS.
        """

    @abstractmethod
    def instantiate_loggers(self, log_level: int) -> None:
        """Instantiate the loggers for the module."""

    def get_config(self) -> Veg2HabConfig:
        return Veg2HabConfig()
