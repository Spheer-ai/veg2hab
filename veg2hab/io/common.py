import json
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import ClassVar, Dict, List, NamedTuple, Optional, Tuple, Union

import geopandas as gpd
from pydantic import BaseModel as _BaseModel
from pydantic import BaseSettings, Field, validator
from typing_extensions import List, Literal

from veg2hab import enums
from veg2hab.criteria import OverrideCriterium
from veg2hab.enums import MaybeBoolean, WelkeTypologie


class BaseModel(_BaseModel):
    class Config:
        extra = "forbid"


class AccessDBInputs(BaseModel):
    label: ClassVar[str] = "1a_digitale_standaard"
    description: ClassVar[str] = "Inladen van vegkartering o.b.v. de digitale standaard"

    shapefile: str = Field(
        description="Vegetatiekartering (geovectorbestand / shapefile)",
    )
    elmid_col: str = Field(
        description="De kolomnaam van de ElementID in de Shapefile; deze wordt gematched aan de Element tabel in de AccessDB",
    )
    access_mdb_path: Path = Field(
        description="Bestandslocatie van de .mdb file van de digitale standaard",
    )
    welke_typologie: Literal[WelkeTypologie.SBB, WelkeTypologie.rVvN] = Field(
        description='De typologie van de vegetatiekartering. ("SBB", "rVvN")',
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

    @validator("welke_typologie", pre=True)
    def parse_vegetatiekundig_identiek_json(cls, value):
        if isinstance(value, str):
            return WelkeTypologie(value)


class ShapefileInputs(BaseModel):
    label: ClassVar[str] = "1b_vector_bestand"
    description: ClassVar[str] = "Inladen van vegkartering o.b.v. een vector bestand"

    shapefile: str = Field(
        description="Vegetatiekartering (geovectorbestand)",
    )
    elmid_col: Optional[str] = Field(
        description="De kolomnaam van de ElementID in de Shapefile; uniek per vlak",
    )
    vegtype_col_format: Literal["single", "multi"] = Field(
        description='"single" als complexen in 1 kolom zitten of "multi" als er meerdere kolommen zijn',
    )
    welke_typologie: WelkeTypologie = Field(
        description='Voornaamste typologie van waaruit de vertalingen worden uitgevoerd. ("SBB", "VvN", "rVvN", "SBB en VvN")',
    )
    sbb_col: List[str] = Field(
        default_factory=list,
        description="SBB kolom(men) (verplicht wanneer het voorname type 'SBB' of 'SBB en VvN' is)",
    )
    vvn_col: List[str] = Field(
        default_factory=list,
        description="VvN kolom(men) (verplicht wanneer het voorname type 'VvN' of 'SBB en VvN' is)",
    )
    rvvn_col: List[str] = Field(
        default_factory=list,
        description="rVvN kolom(men) (verplicht wanneer het voorname type 'rVvN' is)",
    )
    perc_col: List[str] = Field(
        default_factory=list,
        description="Percentage kolom(men) (optioneel)",
    )
    lok_vegtypen_col: List[str] = Field(
        default_factory=list,
        description="Lokale vegetatietypen kolom(men) (optioneel)",
    )
    split_char: Optional[str] = Field(
        default="+",
        description='Karakter waarop de complexe vegetatietypen gesplitst moeten worden (voor complexen (bv "16aa2+15aa"))',
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


class StackVegKarteringInputs(BaseModel):
    label: ClassVar[str] = "2_optioneel_stapel_veg"
    description: ClassVar[str] = "Stapel verschillende vegetatiekarteringen"

    shapefile: List[str] = Field(
        description="Vegetatiekarteringen, op volgerde van prioriteit (belangrijkste eerst). Outputs van stap 1",
    )
    output: Optional[Path] = Field(
        default=None,
        description="Output bestand (optioneel), indien niet gegeven wordt er een bestandsnaam gegenereerd",
    )


class OverrideCriteriumIO(BaseModel):
    mits: str
    truth_value: Literal["WAAR", "ONWAAR", "ONDUIDELIJK"]
    override_geometry: Optional[str] = None
    truth_value_outside: Optional[Literal["WAAR", "ONWAAR", "ONDUIDELIJK"]] = None

    @validator("mits")
    def validate_mits(cls, value):
        if value not in enums.STR_MITSEN:
            raise ValueError(
                f"Invalide mits: mits moet exact overeenkomen met een mits uit de deftabel"
            )
        return value

    @validator("override_geometry")
    def validate_override_geometry(cls, value):
        if value == "" or value == "None":
            return None
        return value

    @validator("truth_value_outside", pre=True)
    def validate_truth_value_outside(cls, value):
        if value == "" or value == "None":
            return None
        return value

    @staticmethod
    def parse_list_of_strings(
        values: List[Tuple[str, str, str, str]]
    ) -> List["OverrideCriteriumIO"]:
        return [
            OverrideCriteriumIO(
                mits=mits,
                truth_value=truth_value,
                override_geometry=override_geometry,
                truth_value_outside=truth_value_outside,
            )
            for mits, truth_value, override_geometry, truth_value_outside in values
        ]

    @staticmethod
    def _str_to_maybeboolean(
        value: Optional[Literal["WAAR", "ONWAAR", "ONDUIDELIJK"]]
    ) -> Optional[MaybeBoolean]:
        if value is None:
            return None
        mapping = {
            "WAAR": MaybeBoolean.TRUE,
            "ONWAAR": MaybeBoolean.FALSE,
            "ONDUIDELIJK": MaybeBoolean.CANNOT_BE_AUTOMATED,
        }
        return mapping[value]

    @staticmethod
    def _read_overrride_geometry(value: Optional[str]) -> Optional[gpd.GeoSeries]:
        if value is None:
            return None
        p = Interface.get_instance().shape_id_to_filename(value)
        return gpd.read_file(p).geometry

    def to_override_criterium(self) -> OverrideCriterium:
        if (self.override_geometry is None) != (self.truth_value_outside is None):
            raise ValueError(
                "Zowel 'Geometrie' als 'Mits uitkomst buiten geometrie' moeten beide gezet zijn of beide niet"
            )
        if self.truth_value == self.truth_value_outside:
            raise ValueError(
                "Mits uitkomst binnen geometrie en buiten geometrie kunnen niet gelijk zijn. Laat geometrie leeg wanneer dit niet nodig is."
            )

        return OverrideCriterium(
            mits=self.mits,
            truth_value=self._str_to_maybeboolean(self.truth_value),
            override_geometry=self._read_overrride_geometry(self.override_geometry),
            truth_value_outside=self._str_to_maybeboolean(self.truth_value_outside),
        )


class ApplyDefTabelInputs(BaseModel):
    label: ClassVar[str] = "3_definitietabel_en_mitsen"
    description: ClassVar[str] = "Pas de definitie tabel toe en check de mitsen"

    shapefile: str = Field(
        description="Vegetatiekartering (output van stap 1 of 2)",
    )
    output: Optional[Path] = Field(
        default=None,
        description="Output bestand (optioneel), indien niet gegeven wordt er een bestandsnaam gegenereerd",
    )
    override_dict: List[OverrideCriteriumIO] = Field(
        default_factory=list,
        description="Lijst met de mitsen en de OverrideCriteria door welke ze moeten worden vervangen",
    )

    def as_override_dict(self) -> Dict[str, OverrideCriterium]:
        crits = [c.to_override_criterium() for c in self.override_dict]
        return {c.mits: c for c in crits}


class ApplyMozaiekInputs(BaseModel):
    label: ClassVar[str] = "4_mozaiekregels"
    description: ClassVar[str] = "Pas de mozaiekregels toe "

    shapefile: str = Field(
        description="Habitattypekartering (output van stap 3)",
    )
    output: Optional[Path] = Field(
        default=None,
        description="Output bestand (optioneel), indien niet gegeven wordt er een bestandsnaam gegenereerd",
    )


class ApplyFunctioneleSamenhangInputs(BaseModel):
    label: ClassVar[str] = "5_functionele_samenhang_en_min_opp"
    description: ClassVar[
        str
    ] = "Functionele samenhang en creeer de definitieve habitatkaart"

    shapefile: str = Field(
        description="Habitattypekartering (output van stap 4)",
    )
    output: Optional[Path] = Field(
        default=None,
        description="Output bestand (optioneel), indien niet gegeven wordt er een bestandsnaam gegenereerd",
    )


class Veg2HabConfig(BaseSettings):
    class Config:
        env_prefix = "VEG2HAB_"

    combineer_karteringen_weglaten_threshold: float = Field(
        default=0.0001,
        description="Threshold in m^2 voor het weglaten van vlakken na het combineren van karteringen",
    )

    mozaiek_threshold: float = Field(
        default=95.0,
        description="Threshold voor het bepalen of een vlak in het mozaiek ligt",
    )
    mozaiek_als_rand_threshold: float = Field(
        default=25.0,
        description="Threshold voor het bepalen of een vlak langs de rand van het mozaiek ligt",
    )
    mozaiek_minimum_bedekking: float = Field(
        default=90.0,
        description="Minimum percentage dat geschikte habitattypen/vegetatietypen in een omringend vlak moet hebben voordat deze mee telt",
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

    niet_geautomatiseerde_rvvn: List[str] = Field(
        default=[
            "r100",
            "r200",
            "r300",
            "r400",
        ],
        description="rVvN vegetatietypen die niet geautomatiseerd kunnen worden",
    )

    functionele_samenhang_vegetatiekundig_identiek: Dict[str, str] = Field(
        default={
            "H2130": "H2130/H4030",
            "H4030": "H2130/H4030",
        },
        description="Vertaler van vegetatiekundig identieke habitattypen naar een gemene string",
    )

    @validator("functionele_samenhang_vegetatiekundig_identiek", pre=True)
    def parse_vegetatiekundig_identiek_json(cls, value):
        try:
            return json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError:
            raise ValueError(
                "Invalid JSON string for functionele_samenhang_vegetatiekundig_identiek"
            )

    # (vanaf percentage (inclusief), buffer afstand)
    functionele_samenhang_buffer_distances: List[Tuple[float, float]] = Field(
        default=[
            (100, 10.01),
            (90, 5.01),
            (50, 0.01),
        ],
        description="Lijst met (vanaf percentage (incl), tot percentage (excl), buffer afstand) tuples voor het bepalen van functionele samenhang",
    )

    # json dump omdat een dictionary niet via environment variables geupdate zou kunnen worden
    minimum_oppervlak_exceptions: Dict[str, float] = Field(
        default={
            "H6110": 10,
            "H7220": 10,
            "H2180_A": 1000,
            "H2180_B": 1000,
            "H2180_C": 1000,
            "H9110": 1000,
            "H9120": 1000,
            "H9160_A": 1000,
            "H9160_B": 1000,
            "H9190": 1000,
            "H91D0": 1000,
            "H91E0_A": 1000,
            "H91E0_B": 1000,
            "H91E0_C": 1000,
            "H91F0": 1000,
        },
        description="Minimum oppervlakken per habitattype",
    )

    @validator("minimum_oppervlak_exceptions", pre=True)
    def parse_minimum_oppervlak_exceptions_json(cls, value):
        try:
            return json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string for minimum_oppervlak_exceptions_raw")

    minimum_oppervlak_default: float = Field(
        default=100,
        description="Minimum oppervlak voor een habitattype",
    )

    def get_minimum_oppervlak_for_habtype(self, habtype: str) -> float:
        return self.minimum_oppervlak_exceptions.get(
            habtype, self.minimum_oppervlak_default
        )


class Interface(metaclass=ABCMeta):
    """Singleton class that defines the interface for the different UI systems."""

    _instance = None

    # make the constructor private
    def __new__(cls):
        raise TypeError(
            "Interface is a singleton class and cannot only be accessed through get_instance"
        )

    @classmethod
    def get_instance(cls):
        if Interface._instance is None:
            Interface._instance = object.__new__(cls)
        return Interface._instance

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
