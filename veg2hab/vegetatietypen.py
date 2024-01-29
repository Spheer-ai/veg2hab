from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import ClassVar, Optional, Union

import pandas as pd


@dataclass()
class SBB:
    """
    Format van SBB codes:
    ## is cijfer ('1', '5', '10', '32', zonder voorloopnul, dus geen '01' of '04')
    x is lowercase letter ('a', 'b', 'c' etc)
    Normale SBB: ##x##x: zoals 14e1a
    Behalve klasse is elke taxonomiegroep is optioneel, zolang de meer specifieke ook
    afwezig zijn (klasse-verbond-associatie is valid, klasse-associatie-subassociatie niet)
    Derivaatgemeenschappen: {normale sbb}/x, zoals 16b/a
    Rompgemeenschappen: {normale sbb}-x, zoals 16-b
    """

    basis_sbb: ClassVar = re.compile(
        r"(?P<klasse>[1-9][0-9]?)((?P<verbond>[a-z])((?P<associatie>[1-9])(?P<subassociatie>[a-z])?)?)?"
    )
    # 14e1a           1    4                   e                     1                       a
    gemeenschap: ClassVar = re.compile(r"(?P<type>[-\/])(?P<gemeenschap>[a-z])$")
    # 16b/a                                        /                     a

    klasse: str
    verbond: Optional[str]
    associatie: Optional[str]
    subassociatie: Optional[str]
    derivaatgemeenschap: Optional[str]
    rompgemeenschap: Optional[str]
    max_match_level: int

    def __init__(self, code: str):
        assert isinstance(code, str), "Code is not a string"

        # Zet de gemeenschappen alvast op None zodat we ze kunnen overschrijven als het een gemeenschap is
        self.derivaatgemeenschap = None
        self.rompgemeenschap = None

        match = self.gemeenschap.search(code)
        if match:
            # Strippen van gemeenschap
            code = code[:-2]
            if match.group("type") == "/":
                self.derivaatgemeenschap = match.group("gemeenschap")
            elif match.group("type") == "-":
                self.rompgemeenschap = match.group("gemeenschap")
            else:
                assert (
                    False
                ), "Onmogelijk om hier te komen; groep 'type' moet '/' of '-' zijn"

        match = self.basis_sbb.fullmatch(code)
        if match:
            self.klasse = match.group("klasse")
            self.verbond = match.group("verbond")
            self.associatie = match.group("associatie")
            self.subassociatie = match.group("subassociatie")
            # 1 voor elke matchende subgroep, of 1 als het een gemeenschap is
            if not (self.derivaatgemeenschap or self.rompgemeenschap):
                self.max_match_level = sum(
                    1 for subgroup in self.base_SBB_as_tuple() if subgroup
                )
            else:
                self.max_match_level = 1
            return

        raise ValueError()

    def base_SBB_as_tuple(self):
        """
        Returns the base part of the SBB code as a tuple
        """
        return (self.klasse, self.verbond, self.associatie, self.subassociatie)

    def match_up_to(self, other: Optional[SBB]):
        """
        Geeft het aantal subgroepen terug waarin deze SBB overeenkomt met de andere
        """
        if other is None:
            return 0

        assert isinstance(other, SBB), "Other is not an SBB"

        if (
            self.derivaatgemeenschap
            or other.derivaatgemeenschap
            or self.rompgemeenschap
            or other.rompgemeenschap
        ):
            # Return 1 als ze dezelfde zijn, 0 als ze niet dezelfde zijn
            return int(self == other)

        self_tuple = self.base_SBB_as_tuple()
        other_tuple = other.base_SBB_as_tuple()

        for i, (self_group, other_group) in enumerate(zip(self_tuple, other_tuple)):
            if (self_group is None) and (other_group is None):
                return i
            if self_group == other_group:
                continue
            if (self_group != other_group) and (other_group is None):
                return i
            return 0
        return len(self_tuple)

    @staticmethod
    def validate(code: str):
        """
        Validate dat t een valide SBB code is
        """
        # Strippen van evt rompgemeenschap of derivaatgemeenschap
        code_gemeenschap = re.sub(SBB.gemeenschap, "", code)

        return SBB.basis_sbb.fullmatch(code) or SBB.basis_sbb.fullmatch(
            code_gemeenschap
        )

    @classmethod
    def validate_pandas_series(cls, series: pd.Series, print_invalid: bool = False):
        """
        Valideert een pandas series van SBB codes
        NATypes worden als valide beschouwd
        """
        series = series.astype("string")

        # NATypes op true zetten, deze zijn in principe valid maar validate verwacht str
        valid_mask = series.apply(lambda x: cls.validate(x) if pd.notna(x) else True)

        if print_invalid:
            if valid_mask.all():
                print("Alle SBB codes zijn valide")
            else:
                invalid = series[~valid_mask]
                print(f"De volgende SBB codes zijn niet valide: \n{invalid}")

        return valid_mask.all()


def convert_string_to_SBB(code):
    """
    Functie om pandas om te zetten naar SBB klasse
    """
    # Check dat het een string is
    if isinstance(code, str):
        return SBB(code)
    else:
        assert pd.isnull(code), "Code is not a string or null"
        return code


@dataclass()
class VvN:
    """
    Format van VvN codes:
    ## is cijfer ('1', '5', '10', '32', niet '01' of '04'), x is letter ('a', 'b', 'c' etc)
    Normale VvN: ##xx##x, zoals 42aa1e
    Behalve klasse is elke taxonomiegroep is optioneel, zolang de meer specifieke ook
    afwezig zijn (klasse-orde-verbond is valid, klasse-verbond-associatie niet)
    Rompgemeenschappeen: ## rg ##, zoals 37rg2
    Derivaatgemeenschappen: ## dg ##, zoals 42dg2
    """

    normale_vvn: ClassVar = re.compile(
        r"(?P<klasse>[1-9][0-9]?)((?P<orde>[a-z])((?P<verbond>[a-z])((?P<associatie>[1-9][0-9]?)(?P<subassociatie>[a-z])?)?)?)?"
    )
    # 42aa1e                                         4    2                a                  a                     1                             e
    gemeenschap: ClassVar = re.compile(
        r"(?P<klasse>[1-9][0-9]?)(?P<type>[dr]g)(?P<gemeenschap>[1-9][0-9]?)"
    )
    # 37rg2                                          3    7               r  g                  2

    klasse: str
    orde: Optional[str]
    verbond: Optional[str]
    associatie: Optional[str]
    subassociatie: Optional[str]
    derivaatgemeenschap: Optional[str]
    rompgemeenschap: Optional[str]
    max_match_level: int

    def __init__(self, code: str):
        assert isinstance(code, str), "Code is not a string"

        match = self.gemeenschap.fullmatch(code)
        if match:
            self.klasse = match.group("klasse")
            self.orde = None
            self.verbond = None
            self.associatie = None
            self.subassociatie = None
            self.max_match_level = 1
            if match.group("type") == "dg":
                self.derivaatgemeenschap = match.group("gemeenschap")
                self.rompgemeenschap = None
                return
            elif match.group("type") == "rg":
                self.derivaatgemeenschap = None
                self.rompgemeenschap = match.group("gemeenschap")
                return
            else:
                assert (
                    False
                ), "Onmogelijk om hier te komen; groep 'type' moet 'dg' of 'rg' zijn"

        match = self.normale_vvn.fullmatch(code)
        if match:
            self.klasse = match.group("klasse")
            self.orde = match.group("orde")
            self.verbond = match.group("verbond")
            self.associatie = match.group("associatie")
            self.subassociatie = match.group("subassociatie")
            self.derivaatgemeenschap = None
            self.rompgemeenschap = None
            # 1 voor elke niet None subgroep
            self.max_match_level = sum(
                1
                for subgroup in [
                    self.klasse,
                    self.orde,
                    self.verbond,
                    self.associatie,
                    self.subassociatie,
                ]
                if subgroup
            )
            return
        raise ValueError()

    def normal_VvN_as_tuple(self):
        if self.derivaatgemeenschap or self.rompgemeenschap:
            raise ValueError("Dit is geen normale (niet derivaat-/rompgemeenschap) VvN")
        return (
            self.klasse,
            self.orde,
            self.verbond,
            self.associatie,
            self.subassociatie,
        )

    def match_up_to(self, other: VvN):
        """
        Geeft het aantal subgroepen terug waarin deze VvN overeenkomt met de andere
        """
        if (
            self.derivaatgemeenschap
            or other.derivaatgemeenschap
            or self.rompgemeenschap
            or other.rompgemeenschap
        ):
            # Return 1 als ze dezelfde zijn, 0 als ze niet dezelfde zijn
            return int(self == other)

        self_tuple = self.normal_VvN_as_tuple()
        other_tuple = other.normal_VvN_as_tuple()

        for i, (self_group, other_group) in enumerate(zip(self_tuple, other_tuple)):
            if (self_group is None) and (other_group is None):
                return i
            if self_group == other_group:
                continue
            if (self_group != other_group) and (other_group is None):
                return i
            return 0
        return len(self_tuple)

    @classmethod
    def validate(cls, code: str):
        """
        Valideert dat het aan onze opmaak van VvN codes voldoet
        """
        return cls.normale_vvn.fullmatch(code) or cls.gemeenschap.fullmatch(code)

    @classmethod
    def validate_pandas_series(cls, series: pd.Series, print_invalid: bool = False):
        """
        Valideert een pandas series van VvN codes
        NATypes worden als valide beschouwd
        """
        series = series.astype("string")

        # NATypes op true zetten, deze zijn in principe valid maar validate verwacht str
        valid_mask = series.apply(lambda x: cls.validate(x) if pd.notna(x) else True)

        if print_invalid:
            if valid_mask.any():
                print("Alle VvN codes zijn valide")
            else:
                invalid = series[~valid_mask]
                print(f"De volgende VvN codes zijn niet valide: \n{invalid}")

        return valid_mask.all()


def opschonen_SBB_pandas_series(series: pd.Series):
    """
    Voert een aantal opschoningen uit op een pandas series van SBB codes
    Hierna zijn ze nog niet per se valide, dus check dat nog
    """
    series = series.astype("string")

    # Verwijderen prefix (voor deftabel)
    series = series.str.replace("SBB-", "")
    # Verwijderen xxx suffix (voor deftabel)
    series = series.str.replace("-xxx [08-f]", "", regex=False)
    # Maak lowercase
    series = series.str.lower()
    # Verwijderen whitespace
    series = series.str.replace(" ", "")
    # Vervangen 300 / 400 door nan
    series = series.replace(["300", "400"], pd.NA)
    # Regex vervang 0[1-9] door [1-9]
    series = series.str.replace(r"0([1-9])", r"\1", regex=True)

    return series


def opschonen_VvN_pandas_series(series: pd.Series):
    """
    Voert een aantal opschoningen uit op een pandas series van VvN codes
    Hierna zijn ze nog niet per se valide, dus check dat nog
    """
    series = series.astype("string")

    # Maak lowercase
    series = series.str.lower()
    # Verwijderen whitespace uit VvN
    series = series.str.replace(" ", "")
    # Verwijderen '-' (voor deftabel)
    series = series.str.replace("-", "")
    # Converteren rompgemeenschappen en derivaaatgemeenschappen (voor deftabel)
    series = series.str.replace(r"\[.*\]", "", regex=True)
    # Verwijderen haakjes uit Vvn (voor wwl)
    series = series.str.replace("[()]", "", regex=True)
    # Verwijderen p.p. uit VvN (voor wwl)
    series = series.str.replace("p.p.", "")
    # regex vervang 0[1-9] door [1-9]
    series = series.str.replace("0([1-9])", r"\1", regex=True)

    return series


def convert_string_to_VvN(code):
    """
    Functie om pandas om te zetten naar VvN klasse
    """
    # Check dat het geen nan is
    if isinstance(code, str):
        return VvN(code)
    else:
        assert pd.isnull(code), "Code is not a string or null"
        return code
