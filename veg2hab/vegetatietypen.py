from __future__ import annotations

import re
from typing import Union

import pandas as pd


class VegetatieType:
    """
    Base class for vegetatietypen (SBB en VvN)
    """

    def validate(self, code: str):
        raise NotImplementedError

    @staticmethod
    def get_invalid_mask_pandas_series(code_type: Union[SBB, VvN], series: pd.Series):
        """
        Validates a pandas series of codes
        """
        series = series.astype("string")

        # NATypes op true zetten, SBB verwacht str
        invalid_mask = ~series.apply(
            lambda x: code_type.validate(x) if pd.notna(x) else True
        )

        return invalid_mask


class SBB(VegetatieType):
    """
    Format van SBB codes:
    # is cijfer, x is letter
    Normale SBB: ## x x #: zoals 14e1a
    Elke toevoeging na de eerste ## is optioneel, zolang de latere ook afwezig zijn (14e is valid, 14a niet)
    De eerste van 2 cijfers mag geen 0 zijn (5d2 is valid, 05d2 niet)
    Derivaatgemeenschappen: {normale sbb} / x, zoals 16B/a
    Rompgemeenschappen: {normale sbb} - x, zoals 16-b
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
        # TODO: This is a prototype, if possible find some sort of explanation/standard somewhere
        base_sbb = re.compile(r"[1-9][0-9]?([a-z]([1-9]([a-z])?)?)?")
        # 14E1a                     1    4      E     1     a
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

    @staticmethod
    def validate_pandas_series(series: pd.Series, print_invalid: bool = False):
        invalid_mask = VegetatieType.get_invalid_mask_pandas_series(SBB, series)

        if print_invalid:
            if ~invalid_mask.any():
                print("Alle SBB codes zijn valide")
            else:
                invalid = series[invalid_mask]
                print(f"De volgende SBB codes zijn niet valide: \n{invalid}")

        return ~invalid_mask.any()


class VvN(VegetatieType):
    """
    Format van VvN codes:
    # is cijfer, x is letter
    Normale VvN: ## x x ## x, zoals 42aa1e
    Elke toevoeging na de eerste ## is optioneel, zolang de latere ook afwezig zijn (42a is valid, 42a1 niet)
    De eerste van 2 cijfers mag geen 0 zijn (8bb2 is valid, 08bb02 niet)
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
        # TODO: test this works - should work tested some examples yet to test the wwl
        normale_vvn = re.compile(r"[1-9][0-9]?([a-z]([a-z]([1-9][0-9]?([a-z])?)?)?)?")
        # 42Aa1e            4    2       A    a     1           e
        rompgemeenschap = re.compile(r"[1-9][0-9]?rg[1-9][0-9]?")
        # 37RG2                 3    7    RG 2
        derivaatgemeenschap = re.compile(r"[1-9][0-9]?dg[1-9][0-9]?")
        # 42DG2                      4    3    DG 2
        if (
            normale_vvn.fullmatch(code)
            or rompgemeenschap.fullmatch(code)
            or derivaatgemeenschap.fullmatch(code)
        ):
            return True

        return False

    @staticmethod
    def validate_pandas_series(series: pd.Series, print_invalid: bool = False):
        invalid_mask = VegetatieType.get_invalid_mask_pandas_series(VvN, series)

        if print_invalid:
            if ~invalid_mask.any():
                print("Alle VvN codes zijn valide")
            else:
                invalid = series[invalid_mask]
                print(f"De volgende VvN codes zijn niet valide: \n{invalid}")

        return ~invalid_mask.any()
