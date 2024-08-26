from __future__ import annotations

import logging
import re
from typing import Any, ClassVar, Optional, Union

import pandas as pd
from pydantic import BaseModel as PydanticBaseModel
from typing_extensions import Self

from veg2hab.enums import MatchLevel
from veg2hab.io.common import Interface


class BaseModel(PydanticBaseModel):
    class Config:
        extra = "forbid"


class SBB(BaseModel):
    """
    Format van SBB codes:
    ## is cijfer ('1', '5', '10', '32', zonder voorloopnul, dus geen '01' of '04')
    x is lowercase letter ('a', 'b', 'c' etc)
    Normale SBB: ##x##x: zoals 14e1a
    Behalve klasse is elke taxonomiegroep optioneel, zolang de meer specifieke ook
    afwezig zijn (klasse-verbond-associatie (##x##) is valid, klasse-associatie-subassociatie (####x) niet)
    Derivaatgemeenschappen: {normale sbb}/x, zoals 16b/a
    Rompgemeenschappen: {normale sbb}-x, zoals 16-b
    """

    basis_sbb: ClassVar[Any] = re.compile(
        r"(?P<klasse>[1-9][0-9]?)((?P<verbond>[a-z])((?P<associatie>[1-9])(?P<subassociatie>[a-z])?)?)?"
    )
    # 14e1a           1    4                   e                     1                       a
    gemeenschap: ClassVar[Any] = re.compile(r"(?P<type>[-\/])(?P<gemeenschap>[a-z])$")
    # 16b/a                                        /                     a

    klasse: str
    verbond: Optional[str] = None
    associatie: Optional[str] = None
    subassociatie: Optional[str] = None
    derivaatgemeenschap: Optional[str] = None
    rompgemeenschap: Optional[str] = None

    @classmethod
    def from_code(cls, code: str) -> Self:
        assert isinstance(code, str), "Code is not a string"
        niet_geautomatiseerde_sbb = (
            Interface.get_instance().get_config().niet_geautomatiseerde_sbb
        )
        if code in niet_geautomatiseerde_sbb:
            return cls(klasse=code)

        kwargs = {}
        match = cls.gemeenschap.search(code)
        if match:
            # Strippen van gemeenschap
            code = code[:-2]
            if match.group("type") == "/":
                kwargs["derivaatgemeenschap"] = match.group("gemeenschap")
            elif match.group("type") == "-":
                kwargs["rompgemeenschap"] = match.group("gemeenschap")
            else:
                raise ValueError(f"Invalide gemeenschap: {code}")

        match = cls.basis_sbb.fullmatch(code)
        if match:
            kwargs["klasse"] = match.group("klasse")
            kwargs["verbond"] = match.group("verbond")
            kwargs["associatie"] = match.group("associatie")
            kwargs["subassociatie"] = match.group("subassociatie")
            return cls(**kwargs)

        raise ValueError(f"Invalid SBB code: '{code}'")

    def base_SBB_as_tuple(
        self,
    ) -> tuple[str, Union[str, None], Union[str, None], Union[str, None]]:
        """
        Returns the base part of the SBB code as a tuple
        """
        return (self.klasse, self.verbond, self.associatie, self.subassociatie)

    @classmethod
    def from_string(cls, code: Union[str, None]) -> Union[SBB, None]:
        if pd.isnull(code) or code == "":
            return None
        return cls.from_code(code)

    def match_up_to(self, other: Optional[SBB]) -> MatchLevel:
        """
        Geeft het aantal subgroepen terug waarin deze SBB overeenkomt met de andere
        """
        match_levels = [
            MatchLevel.NO_MATCH,
            MatchLevel.KLASSE_SBB,
            MatchLevel.VERBOND_SBB,
            MatchLevel.ASSOCIATIE_SBB,
            MatchLevel.SUBASSOCIATIE_SBB,
        ]

        if other is None:
            return match_levels[0]
        assert isinstance(other, SBB), "Other is not an SBB"

        if (
            self.derivaatgemeenschap
            or other.derivaatgemeenschap
            or self.rompgemeenschap
            or other.rompgemeenschap
        ):
            # Return 1 als ze dezelfde zijn, 0 als ze niet dezelfde zijn
            return MatchLevel.GEMEENSCHAP_SBB if self == other else MatchLevel.NO_MATCH

        self_tuple = self.base_SBB_as_tuple()
        other_tuple = other.base_SBB_as_tuple()

        for i, (self_group, other_group) in enumerate(zip(self_tuple, other_tuple)):
            if (self_group is None) and (other_group is None):
                return match_levels[i]
            if self_group == other_group:
                continue
            if (self_group != other_group) and (other_group is None):
                return match_levels[i]
            return match_levels[0]
        return match_levels[len(self_tuple)]

    @classmethod
    def validate_code(cls, code: str) -> bool:
        """
        Checkt of een string voldoet aan de SBB opmaak
        """
        # Strippen van evt rompgemeenschap of derivaatgemeenschap
        code_gemeenschap = re.sub(cls.gemeenschap, "", code)

        return cls.basis_sbb.fullmatch(code) or cls.basis_sbb.fullmatch(
            code_gemeenschap
        )

    @classmethod
    def validate_pandas_series(
        cls, series: pd.Series, print_invalid: bool = False
    ) -> bool:
        """
        Valideert een pandas series van SBB codes
        NATypes worden als valide beschouwd
        """
        series = series.astype("string")

        # NATypes op true zetten, deze zijn in principe valid maar validate verwacht str
        valid_mask = series.apply(
            lambda x: cls.validate_code(x) if pd.notna(x) else True
        )

        if print_invalid:
            if valid_mask.all():
                logging.info("Alle SBB codes zijn valide")
            else:
                invalid = series[~valid_mask]
                logging.warning(f"De volgende SBB codes zijn niet valide: \n{invalid}")

        return valid_mask.all()

    def __str__(self):
        classification = [x for x in self.base_SBB_as_tuple() if x is not None]
        if self.derivaatgemeenschap:
            classification.append("/")
            classification.append(self.derivaatgemeenschap)
        if self.rompgemeenschap:
            classification.append("-")
            classification.append(self.rompgemeenschap)
        return "".join(classification)

    def __hash__(self):
        return hash(
            (
                self.klasse,
                self.verbond,
                self.associatie,
                self.subassociatie,
                self.derivaatgemeenschap,
                self.rompgemeenschap,
            )
        )

    @staticmethod
    def opschonen_series(series: pd.Series) -> pd.Series:
        """
        Voert een aantal opschoningen uit op een pandas series van SBB codes
        Hierna zijn ze nog niet per se valide, dus check dat nog
        """
        series = series.astype("string")
        # Van alle smaken NA gewoon None maken
        series = series.apply(lambda x: None if pd.isna(x) else x)
        # Verwijderen prefix (voor deftabel)
        series = series.str.replace("SBB-", "")
        # Verwijderen xxx suffix (voor deftabel)
        series = series.str.replace("-xxx [08-f]", "", regex=False)
        # Maak lowercase
        series = series.str.lower()
        # Verwijderen whitespace
        series = series.str.replace(" ", "")
        series = series.str.strip()
        # Vervangen 0[1-9] door [1-9]
        series = series.str.replace(r"0([1-9])", r"\1", regex=True)
        # Vervangen enkel "-" of "x" vegtypen door None
        series = series.apply(
            lambda x: None if (pd.notna(x) and x in ["-", "x"]) else x
        )
        # Vervang lege of door opschoningen hierboven leeg gemaakte strings door None
        series = series.apply(lambda x: None if pd.isnull(x) or x == "" else x)

        return series


class VvN(BaseModel):
    """
    Format van VvN codes:
    ## is cijfer ('1', '5', '10', '32', niet '01' of '04'), x is letter ('a', 'b', 'c' etc)
    Normale VvN: ##xx##x, zoals 42aa1e
    Behalve klasse is elke taxonomiegroep optioneel, zolang de meer specifieke ook
    afwezig zijn (klasse-orde-verbond is valid, klasse-verbond-associatie niet)
    Rompgemeenschappeen: ## rg ##, zoals 37rg2
    Derivaatgemeenschappen: ## dg ##, zoals 42dg2
    """

    normale_vvn: ClassVar[Any] = re.compile(
        r"(?P<klasse>[1-9][0-9]?)((?P<orde>[a-z])((?P<verbond>[a-z])((?P<associatie>[1-9][0-9]?)(?P<subassociatie>[a-z])?)?)?)?"
    )
    # 42aa1e          4    2                a                  a                     1                             e
    gemeenschap: ClassVar[Any] = re.compile(
        r"(?P<klasse>[1-9][0-9]?)(?P<type>[dr]g)(?P<gemeenschap>[1-9][0-9]?)"
    )
    # 37rg2           3    7               r  g                  2

    klasse: str
    orde: Optional[str] = None
    verbond: Optional[str] = None
    associatie: Optional[str] = None
    subassociatie: Optional[str] = None
    derivaatgemeenschap: Optional[str] = None
    rompgemeenschap: Optional[str] = None

    @classmethod
    def from_code(cls, code: str):
        assert isinstance(code, str), "Code is not a string"
        match = cls.gemeenschap.fullmatch(code)
        if match:
            kwargs = {"klasse": match.group("klasse")}
            if match.group("type") == "dg":
                kwargs["derivaatgemeenschap"] = match.group("gemeenschap")
                return cls(**kwargs)
            elif match.group("type") == "rg":
                kwargs["rompgemeenschap"] = match.group("gemeenschap")
                return cls(**kwargs)
            else:
                raise ValueError(f"Invalide gemeenschap: {code}")

        match = cls.normale_vvn.fullmatch(code)
        if match:
            return cls(
                klasse=match.group("klasse"),
                orde=match.group("orde"),
                verbond=match.group("verbond"),
                associatie=match.group("associatie"),
                subassociatie=match.group("subassociatie"),
            )

        raise ValueError(f"Invalid VvN code: '{code}'")

    @classmethod
    def from_string(cls, code) -> Union[VvN, None]:
        if pd.isnull(code) or code == "":
            return None
        return cls.from_code(code)

    def normal_VvN_as_tuple(
        self,
    ) -> tuple[
        str, Union[str, None], Union[str, None], Union[str, None], Union[str, None]
    ]:
        if self.derivaatgemeenschap or self.rompgemeenschap:
            raise ValueError("Dit is geen normale (niet derivaat-/rompgemeenschap) VvN")
        return (
            self.klasse,
            self.orde,
            self.verbond,
            self.associatie,
            self.subassociatie,
        )

    def match_up_to(self, other: Optional[VvN]) -> MatchLevel:
        """
        Geeft het aantal subgroepen terug waarin deze VvN overeenkomt met de andere
        """
        match_levels = [
            MatchLevel.NO_MATCH,
            MatchLevel.KLASSE_VVN,
            MatchLevel.ORDE_VVN,
            MatchLevel.VERBOND_VVN,
            MatchLevel.ASSOCIATIE_VVN,
            MatchLevel.SUBASSOCIATIE_VVN,
        ]

        if other is None:
            return match_levels[0]
        assert isinstance(other, VvN), "Other is not an VvN"

        if (
            self.derivaatgemeenschap
            or other.derivaatgemeenschap
            or self.rompgemeenschap
            or other.rompgemeenschap
        ):
            # Return 1 als ze dezelfde zijn, 0 als ze niet dezelfde zijn
            return MatchLevel.GEMEENSCHAP_VVN if self == other else MatchLevel.NO_MATCH

        self_tuple = self.normal_VvN_as_tuple()
        other_tuple = other.normal_VvN_as_tuple()

        for i, (self_group, other_group) in enumerate(zip(self_tuple, other_tuple)):
            if (self_group is None) and (other_group is None):
                return match_levels[i]
            if self_group == other_group:
                continue
            if (self_group != other_group) and (other_group is None):
                return match_levels[i]
            return match_levels[0]
        return match_levels[len(self_tuple)]

    @classmethod
    def validate_code(cls, code: str) -> bool:
        """
        Checkt of een string voldoet aan de VvN opmaak
        """
        return cls.normale_vvn.fullmatch(code) or cls.gemeenschap.fullmatch(code)

    @classmethod
    def validate_pandas_series(
        cls, series: pd.Series, print_invalid: bool = False
    ) -> bool:
        """
        Valideert een pandas series van VvN codes
        NATypes worden als valide beschouwd
        """
        series = series.astype("string")

        # NATypes op true zetten, deze zijn in principe valid maar validate verwacht str
        valid_mask = series.apply(
            lambda x: cls.validate_code(x) if pd.notna(x) else True
        )

        if print_invalid:
            if valid_mask.any():
                logging.info("Alle VvN codes zijn valide")
            else:
                invalid = series[~valid_mask]
                logging.warning(f"De volgende VvN codes zijn niet valide: \n{invalid}")

        return valid_mask.all()

    def __str__(self):
        if self.derivaatgemeenschap:
            return f"{self.klasse}dg{self.derivaatgemeenschap}"
        if self.rompgemeenschap:
            return f"{self.klasse}rg{self.rompgemeenschap}"
        classification = [x for x in self.normal_VvN_as_tuple() if x is not None]
        return "".join(classification)

    def __hash__(self):
        return hash(
            (
                self.klasse,
                self.orde,
                self.verbond,
                self.associatie,
                self.subassociatie,
                self.derivaatgemeenschap,
                self.rompgemeenschap,
            )
        )

    @staticmethod
    def opschonen_series(series: pd.Series) -> pd.Series:
        """
        Voert een aantal opschoningen uit op een pandas series van VvN codes
        Hierna zijn ze nog niet per se valide, dus check dat nog
        """
        series = series.astype("string")
        # Maak lowercase
        series = series.str.lower()
        # Verwijderen whitespace uit VvN
        series = series.str.replace(" ", "")
        series = series.str.strip()
        # Verwijderen '-' (voor deftabel)
        series = series.str.replace("-", "")
        # Converteren rompgemeenschappen en derivaaatgemeenschappen (voor deftabel)
        series = series.str.replace(r"\[.*\]", "", regex=True)
        # Verwijderen haakjes uit Vvn (voor wwl)
        series = series.str.replace("[()]", "", regex=True)
        # Verwijderen p.p. uit VvN (voor wwl)
        series = series.str.replace("p.p.", "", regex=False)
        # Vervangen 0[1-9] door [1-9]
        series = series.str.replace("0([1-9])", r"\1", regex=True)
        # Vervangen enkel "-" of "x" vegtypen door None
        series = series.apply(
            lambda x: None if (pd.notna(x) and x in ["-", "x"]) else x
        )
        # Vervang lege of door opschoningen hierboven leeg gemaakte strings door None
        series = series.apply(lambda x: None if pd.isnull(x) or x == "" else x)

        return series


class rVvN(BaseModel):
    """
    Format van VvN codes:
    ## is cijfer ('1', '5', '10', '32', niet '01' of '04'), x is letter ('a', 'b', 'c' etc)
    Normale VvN: ##xx##x, zoals 42aa1e
    Behalve klasse is elke taxonomiegroep optioneel, zolang de meer specifieke ook
    afwezig zijn (klasse-orde-verbond is valid, klasse-verbond-associatie niet)
    Rompgemeenschappeen: ## rg ##, zoals 37rg2
    Derivaatgemeenschappen: ## dg ##, zoals 42dg2
    """

    normale_rvvn: ClassVar[Any] = re.compile(
        r"r(?P<klasse>[1-9][0-9]?)((?P<orde>[a-z])((?P<verbond>[a-z])((?P<associatie>[1-9][0-9]?)(?P<subassociatie>[a-z])?)?)?)?"
    )
    # r42aa1e         4    2                a                  a                     1                             e
    gemeenschap: ClassVar[Any] = re.compile(
        r"r(?P<klasse>[1-9][0-9]?)(?P<type>[dr]g)(?P<gemeenschap>[1-9][0-9]?)"
    )
    # r37rg2          3    7               r  g                  2

    klasse: str
    orde: Optional[str] = None
    verbond: Optional[str] = None
    associatie: Optional[str] = None
    subassociatie: Optional[str] = None
    derivaatgemeenschap: Optional[str] = None
    rompgemeenschap: Optional[str] = None

    @classmethod
    def from_code(cls, code: str):
        assert isinstance(code, str), "Code is not a string"

        niet_geautomatiseerde_rvvn = (
            Interface.get_instance().get_config().niet_geautomatiseerde_rvvn
        )
        if code in niet_geautomatiseerde_rvvn:
            return cls(klasse=code)

        match = cls.gemeenschap.fullmatch(code)
        if match:
            kwargs = {"klasse": match.group("klasse")}
            if match.group("type") == "dg":
                kwargs["derivaatgemeenschap"] = match.group("gemeenschap")
                return cls(**kwargs)
            elif match.group("type") == "rg":
                kwargs["rompgemeenschap"] = match.group("gemeenschap")
                return cls(**kwargs)
            else:
                raise ValueError(f"Invalide gemeenschap: {code}")

        match = cls.normale_rvvn.fullmatch(code)
        if match:
            return cls(
                klasse=match.group("klasse"),
                orde=match.group("orde"),
                verbond=match.group("verbond"),
                associatie=match.group("associatie"),
                subassociatie=match.group("subassociatie"),
            )

        raise ValueError(f"Invalid rVvN code: '{code}'")

    @classmethod
    def from_string(cls, code) -> Union[VvN, None]:
        if pd.isnull(code) or code == "":
            return None
        return cls.from_code(code)

    def normal_rVvN_as_tuple(
        self,
    ) -> tuple[
        str, Union[str, None], Union[str, None], Union[str, None], Union[str, None]
    ]:
        if self.derivaatgemeenschap or self.rompgemeenschap:
            raise ValueError("Dit is geen normale (niet derivaat-/rompgemeenschap) VvN")
        return (
            self.klasse,
            self.orde,
            self.verbond,
            self.associatie,
            self.subassociatie,
        )

    def match_up_to(self, other: Optional[VvN]) -> MatchLevel:
        raise NotImplementedError("Match up to is not implemented for rVvN")

    @classmethod
    def validate_code(cls, code: str) -> bool:
        """
        Checkt of een string voldoet aan de VvN opmaak
        """
        return cls.normale_rvvn.fullmatch(code) or cls.gemeenschap.fullmatch(code)

    @classmethod
    def validate_pandas_series(
        cls, series: pd.Series, print_invalid: bool = False
    ) -> bool:
        """
        Valideert een pandas series van rVvN codes
        NATypes worden als valide beschouwd
        """
        series = series.astype("string")

        # NATypes op true zetten, deze zijn in principe valid maar validate verwacht str
        valid_mask = series.apply(
            lambda x: cls.validate_code(x) if pd.notna(x) else True
        )

        if print_invalid:
            if valid_mask.any():
                logging.info("Alle rVvN codes zijn valide")
            else:
                invalid = series[~valid_mask]
                logging.warning(f"De volgende rVvN codes zijn niet valide: \n{invalid}")

        return valid_mask.all()

    def __str__(self):
        if self.derivaatgemeenschap:
            return f"r{self.klasse}dg{self.derivaatgemeenschap}"
        if self.rompgemeenschap:
            return f"r{self.klasse}rg{self.rompgemeenschap}"
        classification = [x for x in self.normal_rVvN_as_tuple() if x is not None]
        return "r" + "".join(classification)

    def __hash__(self):
        return hash(
            (
                self.klasse,
                self.orde,
                self.verbond,
                self.associatie,
                self.subassociatie,
                self.derivaatgemeenschap,
                self.rompgemeenschap,
            )
        )

    @staticmethod
    def opschonen_series(series: pd.Series) -> pd.Series:
        """
        Voert een aantal opschoningen uit op een pandas series van rVvN codes
        Hierna zijn ze nog niet per se valide, dus check dat nog
        """
        series = series.astype("string")
        # Verwijderen Niet overgenomen in Revisie
        series.loc[series == "Niet overgenomen in Revisie"] = None
        series.loc[series == "Niet overgenomen in Revisie (grasland-deel)"] = None
        # Maak lowercase
        series = series.str.lower()
        # Verwijderen whitespace uit VvN
        series = series.str.replace(" ", "")
        series = series.str.strip()
        # Verwijderen '-' (voor deftabel)
        series = series.str.replace("-", "")
        # Converteren rompgemeenschappen en derivaaatgemeenschappen (voor deftabel)
        series = series.str.replace(r"\[.*\]", "", regex=True)
        # Verwijderen haakjes uit Vvn (voor wwl)
        series = series.str.replace("[()]", "", regex=True)
        # Verwijderen p.p. uit VvN (voor wwl)
        series = series.str.replace("p.p.", "", regex=False)
        # Vervangen 0[1-9] door [1-9]
        series = series.str.replace("0([1-9])", r"\1", regex=True)
        # Vervangen enkel "-" of "x" vegtypen door None
        series = series.apply(
            lambda x: None if (pd.notna(x) and x in ["-", "x"]) else x
        )
        # Vervang lege of door opschoningen hierboven leeg gemaakte strings door None
        series = series.apply(lambda x: None if pd.isnull(x) or x == "" else x)

        return series
