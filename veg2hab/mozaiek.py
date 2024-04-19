import json
import warnings
from collections import defaultdict
from numbers import Number
from typing import ClassVar, Dict, List, Optional, Tuple, Union

import geopandas as gpd
import pandas as pd
from pydantic import BaseModel, PrivateAttr

from veg2hab.enums import Kwaliteit, MaybeBoolean


class MozaiekRegel(BaseModel):
    # NOTE: Mogelijk kunnen we in de toekomst van deze structuur af en met maar 1 type mozaiekregel werken

    type: ClassVar[Optional[str]] = None
    _subtypes_: ClassVar[dict] = dict()
    mozaiek_threshold = 90

    def __init_subclass__(cls):
        # Vul de _subtypes_ dict met alle subclasses
        if cls.type is None:
            raise ValueError(
                "You should specify the `type: ClassVar[str] = 'EnCritera'`"
            )
        cls._subtypes_[cls.type] = cls

    def __new__(cls, *args, **kwargs):
        # Maakt de juiste subclass aan op basis van de type parameter
        if cls == MozaiekRegel:
            t = kwargs.pop("type")
            return super().__new__(cls._subtypes_[t])
        return super().__new__(
            cls
        )  # NOTE: wanneer is het niet een beperkendcriterium? TODO Mark vragen

    def dict(self, *args, **kwargs):
        """Ik wil type eigenlijk als ClassVar houden, maar dan wordt ie standaard niet mee geserialized.
        Dit is een hack om dat wel voor elkaar te krijgen.
        """
        data = super().dict(*args, **kwargs)
        data["type"] = self.type
        return data

    def json(self, *args, **kwargs):
        """Same here"""
        return json.dumps(self.dict(*args, **kwargs))

    def is_mozaiek_type_present(self, type) -> bool:
        return isinstance(self, type)

    def check(self, habtype_percentage_dict: Dict) -> None:
        raise NotImplementedError()

    @property
    def evaluation(self) -> MaybeBoolean:
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()


class PlaceholderMozaiekregel(MozaiekRegel):
    type: ClassVar[str] = "PlaceholderMozaiekregel"
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def check(self, habtype_percentage_dict: Dict) -> None:
        self._evaluation = MaybeBoolean.CANNOT_BE_AUTOMATED

    @property
    def evaluation(self) -> MaybeBoolean:
        return self._evaluation

    def __str__(self):
        return "Placeholder mozaiekregel (nog niet geimplementeerd) (nooit waar)"


# class DummyMozaiekregel(Mozaiekregel):
#     # TODO: remove this once no longer needed
#     type: ClassVar[str] = "DummyMozaiekregel"
#     _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

#     def check(self, habtype_percentage_dict: Dict) -> None:
#         self._evaluation = MaybeBoolean.FALSE

#     @property
#     def evaluation(self) -> MaybeBoolean:
#         return self._evaluation


class GeenMozaiekregel(MozaiekRegel):
    type: ClassVar[str] = "GeenMozaiekregel"
    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=MaybeBoolean.TRUE)

    def check(self, habtype_percentage_dict: Dict) -> None:
        self._evaluation = MaybeBoolean.TRUE

    @property
    def evaluation(self) -> MaybeBoolean:
        return self._evaluation

    def __str__(self):
        return "Geen mozaiekregel (altijd waar)"


class StandaardMozaiekregel(MozaiekRegel):
    type: ClassVar[str] = "StandaardMozaiekregel"
    # Habtype waarmee gematcht moet worden
    habtype: str
    alleen_zelfstandig: bool
    alleen_goede_kwaliteit: bool

    keys: List[Tuple[str, bool, Kwaliteit]] = []
    habtype_percentage_dict: Dict = None

    _evaluation: Optional[MaybeBoolean] = PrivateAttr(default=None)

    def determine_keys(self) -> None:
        assert not self.habtype in [
            "H0000",
            "HXXXX",
        ], "Habtype van een mozaiekregel mag niet H0000 of HXXXX zijn"

        # Keys zijn (habtype: str, zelfstandig: bool, kwaliteit: Kwaliteit)
        self.keys = []

        # Zelfstandig Goed is altijd acceptabel
        self.keys.append((self.habtype, True, Kwaliteit.GOED))

        if not self.alleen_zelfstandig:
            self.keys.append((self.habtype, False, Kwaliteit.GOED))

        if not self.alleen_goede_kwaliteit:
            self.keys.append((self.habtype, True, Kwaliteit.MATIG))

            if not self.alleen_zelfstandig:
                self.keys.append((self.habtype, False, Kwaliteit.MATIG))

    def check(self, habtype_percentage_dict: Dict) -> None:
        requested_habtype_percentage = 0
        for key in self.keys:
            requested_habtype_percentage += habtype_percentage_dict[key]

        # Threshold is behaald, dus TRUE
        if requested_habtype_percentage >= self.mozaiek_threshold:
            self._evaluation = MaybeBoolean.TRUE
            return

        unknown_habtype_percentage = habtype_percentage_dict[
            ("HXXXX", True, Kwaliteit.NVT)
        ]
        # Threshold kan nog behaald worden, dus POSTPONE
        if (
            requested_habtype_percentage + unknown_habtype_percentage
            >= self.mozaiek_threshold
        ):
            self._evaluation = MaybeBoolean.POSTPONE
            return

        # Threshold kan niet meer behaald worden, dus FALSE
        self._evaluation = MaybeBoolean.FALSE

    @property
    def evaluation(self) -> MaybeBoolean:
        return self._evaluation

    def __str__(self):
        return f"{'Enkel zelfstandige vegetaties' if self.alleen_zelfstandig else 'Zowel zelfstandige als mozaiekvegetaties'} van {'goede' if self.alleen_goede_kwaliteit else 'goede en matige'} kwaliteit van {self.habtype}. Threshold: {self.mozaiek_threshold}. Geldig voor {self.keys}"


def make_buffered_boundary_overlay_gdf(
    gdf: gpd.GeoDataFrame,
    buffer: Number = 0.1,
) -> Union[None, gpd.GeoDataFrame]:
    """
    Trekt om elk vlak met een mozaiekregel een lijn met afstand "buffer" tot het vlak.
    Deze lijnen worden vervolgens over de originele gdf gelegd en opgeknipt per vlak waar ze over heen liggen.
    Elke sectie opgeknipte lijn krijgt mee hoeveel procent van de totale lijn het is.
    Deze "overlay gdf" wordt vervolgens teruggegeven.

    Hierna kan de HabitatKeuze kolom gejoind worden met de overlay gdf op ElmID.
    De gdf kan hierna gebruikt worden in calc_mozaiek_percentages_from_overlay_gdf
    om te berekenen hoeveel procent van elk habitattype een vlak omringd.
    """
    if buffer < 0:
        raise ValueError(f"Buffer moet positief zijn, maar is {buffer}")

    if buffer == 0:
        warnings.warn("Buffer is 0. Dit kan leiden tot onverwachte resultaten.")

    assert (
        "ElmID" in gdf.columns
    ), f"ElmID niet gevonden in gdf bij make_buffered_boundary_overlay_gdf"

    # TODO: hier is mozaiek_type_present voor gebruiken
    mozaiek_present = gdf.HabitatVoorstel.apply(
        lambda voorstellen: any(
            not isinstance(voorstel.mozaiek, GeenMozaiekregel)
            for sublist in voorstellen
            for voorstel in sublist
        )
    )

    if not mozaiek_present.any():
        return None

    # Eerst trekken we een lijn om alle shapes met mozaiekregels
    buffered_boundary = (
        gdf[mozaiek_present].buffer(buffer).boundary.to_frame(name="geometry")
    )
    assert buffered_boundary.crs == gdf.crs

    # NOTE: Deze buffered_ prefix wordt ook in calc_mozaiek_percentages_from_overlay_gdf gebruikt
    buffered_boundary["buffered_ElmID"] = gdf["ElmID"]
    buffered_boundary["full_line_length"] = buffered_boundary.length

    # Dan leggen we alle lijnen over de originele gdf
    only_needed_cols = gdf[["ElmID", "geometry"]]
    overlayed = gpd.overlay(
        buffered_boundary, only_needed_cols, how="union", keep_geom_type=True
    )
    # We droppen alle lijnen die niet over een vlak liggen
    overlayed = overlayed.dropna(subset=["ElmID"])
    overlayed["part_line_percentage"] = (
        overlayed.length / overlayed.full_line_length
    ) * 100
    return overlayed


def calc_mozaiek_percentages_from_overlay_gdf(
    overlayed: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Ontvangt een overlayed gdf van make_buffered_boundary_overlay_gdf die de HabitatKeuze kolom bevat.
    Uit deze kolom wordt het habitattype gehaald en op basis hiervan wordt per buffered_ElmID
    gekeken door hoeveel procent van elk habitattype het vlak omringd wordt.

    NOTE:
    NOTE: Ter versimpeling wordt nu even aangenomen dat de eerste habitatkeuze per vlak de enige is.
    NOTE:
    """

    assert (
        "HabitatKeuze" in overlayed.columns
    ), "HabitatKeuze niet gevonden in overlayed bij calc_mozaiek_percentages_from_overlay_gdf"

    assert (
        "buffered_ElmID" in overlayed.columns
    ), "buffered_ElmID niet gevonden in overlayed bij calc_mozaiek_percentages_from_overlay_gdf"

    # We maken voor ieder vlak een defaultdict met habitattypes keys naar percentage values
    def row_to_habtype_percentage_dict(group: gpd.GeoDataFrame) -> Dict[str, float]:
        # NOTE: voor nu doen we alsof we maar 1 habtype per vlak hebben

        habtype_percentages = group["part_line_percentage"]
        # Als er geen habitatkeuzes zijn, dan geven we HXXXX terug
        # TODO: pak de grootste keuze als er meerdere zijn
        #       Wat als de grootste nog None is en de kleinere wel een keuze heeft?
        key_tuples = group.HabitatKeuze.apply(
            lambda keuzes:
            # Als len(keuzes) == 0, dan is er geen vegtype opgegeven, dus H0000
            ("H0000", True, Kwaliteit.NVT)
            if len(keuzes) == 0
            else
            # Als de keuze None is, dan is deze nog niet bepaald, dus HXXXX
            ("HXXXX", True, Kwaliteit.NVT)
            if keuzes[0] is None
            else (
                keuzes[0].habtype,
                keuzes[0].zelfstandig,
                keuzes[0].kwaliteit,
            )
        )
        habtype_percentage_dict = defaultdict(int)
        for key, percentage in zip(key_tuples, habtype_percentages):
            habtype_percentage_dict[key] += percentage
        return habtype_percentage_dict

    result = overlayed.groupby("buffered_ElmID").apply(row_to_habtype_percentage_dict)

    # Nu is de index de ElmID, maar we willen een expliciete kolom
    result = result.reset_index()
    result.columns = ["ElmID", "dict"]

    return result


def is_mozaiek_type_present(
    voorstellen: Union[List[List["HabitatVoorstel"]], List["HabitatVoorstel"]],
    mozaiek_type: MozaiekRegel,
) -> bool:
    """
    Geeft True als er in de lijst met habitatvoorstellen eentje met een mozaiekregel van mozaiek_type is
    NOTE: Op het moment wordt dit gebruikt om te kijken of er dummymozaiekregels zijn, en zo ja, dan wordt er HXXXX gegeven.
    NOTE: Zodra mozaiekregels geimplementeerd zijn, kan deze functie mogelijk weg
    """
    # Als we een lijst van lijsten hebben, dan flattenen we die
    if any(isinstance(i, list) for i in voorstellen):
        voorstellen = [item for sublist in voorstellen for item in sublist]
    return any(
        (
            voorstel.mozaiek.is_mozaiek_type_present(mozaiek_type)
            if voorstel.mozaiek is not None
            else False
        )
        for voorstel in voorstellen
    )

    # ------------------------
