from __future__ import annotations

import re
from typing import Union

import pandas as pd


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

    def __init__(self, code: str):
        if not self.validate(code):
            raise ValueError(f"SBB code {code} is niet valide")

        self.code = code

    @staticmethod
    def validate(code: str):
        """
        Validate dat t een valide SBB code is
        """
        base_sbb = re.compile(r"[1-9][0-9]?([a-z]([1-9]([a-z])?)?)?")
        # 14e1a                  1    4      e     1     a
        rompgemeenschap = re.compile(r"-[a-z]$")
        # 14D-a                        - a
        derivaatgemeenschap = re.compile(r"\/[a-z]$")
        # 14A/a                             / a

        # Strippen van evt rompgemeenschap of derivaatgemeenschap
        code_rg = re.sub(rompgemeenschap, "", code)
        code_dg = re.sub(derivaatgemeenschap, "", code)

        if (
            base_sbb.fullmatch(code)
            or base_sbb.fullmatch(code_rg)
            or base_sbb.fullmatch(code_dg)
        ):
            return True

        return False

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

        return valid_mask.any()


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

    def __init__(self, code: str):
        if not self.validate(code):
            raise ValueError(f"VvN code {code} is niet valide")

        self.code = code

    @staticmethod
    def validate(code: str):
        """
        Valideert dat het aan onze opmaak van VvN codes voldoet
        """
        normale_vvn = re.compile(r"[1-9][0-9]?([a-z]([a-z]([1-9][0-9]?([a-z])?)?)?)?")
        # 42aa1e                    4    2       a    a     1           e
        rompgemeenschap = re.compile(r"[1-9][0-9]?rg[1-9][0-9]?")
        # 37rg2                         3    7    rg 2
        derivaatgemeenschap = re.compile(r"[1-9][0-9]?dg[1-9][0-9]?")
        # 42dg2                             4    3    rg 2
        if (
            normale_vvn.fullmatch(code)
            or rompgemeenschap.fullmatch(code)
            or derivaatgemeenschap.fullmatch(code)
        ):
            return True

        return False

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

        return valid_mask.any()


def opschonen_SBB_pandas_series(series: pd.Series):
    """
    Voert een aantal opschoningen uit op een pandas series van SBB codes
    Hierna zijn ze nog niet per se valide, dus check dat nog
    """
    series = series.astype("string")

    # Maak lowercase
    series = series.str.lower()
    # Verwijderen whitespace
    series = series.str.replace(" ", "")
    # Verwijderen prefix (voor deftabel)
    series = series.str.replace("SBB-", "")
    # Verwijderen xxx suffix (voor deftabel)
    series = series.str.replace("-xxx [08-f]", "", regex=False)
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
