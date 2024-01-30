import math
from functools import lru_cache
from pathlib import Path
from typing import List

import pandas as pd

from veg2hab.vegetatietypen import (
    SBB,
    VvN,
    convert_string_to_SBB,
    convert_string_to_VvN,
    opschonen_SBB_pandas_series,
    opschonen_VvN_pandas_series,
)
from veg2hab.vegkartering import VegTypeInfo


class WasWordtLijst:
    def __init__(self, df: pd.DataFrame):
        # Inladen
        self.df = df

        assert df.dtypes["VvN"] == "string", "VvN kolom is geen string"
        assert df.dtypes["SBB"] == "string", "SBB kolom is geen string"

        # Checken
        assert self.check_validity_SBB(
            print_invalid=True
        ), "Niet alle SBB codes zijn valid"
        assert self.check_validity_VvN(
            print_invalid=True
        ), "Niet alle VvN codes zijn valid"

        # Omvormen naar SBB en VvN klasses
        self.df["SBB"] = self.df["SBB"].apply(convert_string_to_SBB)
        self.df["VvN"] = self.df["VvN"].apply(convert_string_to_VvN)

        # Replace pd.NA with None
        # NOTE: kunnen we ook alle rows met een NA gewoon verwijderen? Als we of geen VvN of
        #       geen SBB hebben dan kunnen we het toch niet gebruiken voor het omzetten
        self.df = self.df.where(self.df.notnull(), None)

    @classmethod
    def from_excel(cls, path: Path):
        # NOTE: Dus we nemen de "Opmerking vertaling" kolom niet mee? Even checken nog.
        df = pd.read_excel(
            path, engine="openpyxl", usecols=["VvN", "SBB"], dtype="string"
        )
        return cls(df)

    def check_validity_SBB(self, print_invalid: bool = False):
        """
        Checkt of de SBB codes valide zijn.
        """
        wwl_SBB = self.df["SBB"].astype("string")

        return SBB.validate_pandas_series(wwl_SBB, print_invalid=print_invalid)

    def check_validity_VvN(self, print_invalid: bool = False):
        """
        Checkt of de VvN valide zijn.
        """
        wwl_VvN = self.df["VvN"].astype("string")

        return VvN.validate_pandas_series(wwl_VvN, print_invalid=print_invalid)

    @lru_cache(maxsize=256)
    def match_SBB_to_VvN(self, code: SBB) -> List[VvN]:
        """
        Zoekt de VvN codes die bij een SBB code horen
        """

        assert isinstance(code, SBB), "Code is geen SBB object"

        matching_VvN = self.df[self.df.SBB == code].VvN
        # dropna om niet None uit lege VvN cellen in de wwl als VvN te krijgen
        return matching_VvN.dropna().to_list()

    def toevoegen_VvN_aan_VegTypeInfo(self, info: VegTypeInfo):
        """
        Zoekt adhv SBB codes de bijbehorende VvN codes en voegt deze toe aan de VegetatieTypeInfo
        """
        if info is None:
            raise ValueError("VegTypeInfo is None")

        # Als er geen SBB code is
        if len(info.SBB) == 0:
            return info

        assert all(
            [isinstance(x, SBB) for x in info.SBB]
        ), "SBB is geen lijst van SBB objecten"

        new_VvN = self.match_SBB_to_VvN(info.SBB[0])

        return VegTypeInfo(
            info.percentage,
            SBB=info.SBB,
            VvN=new_VvN,
        )

    def toevoegen_VvN_aan_List_VegTypeInfo(self, infos: List[VegTypeInfo]):
        """
        Voert elke rij door toevoegen_VvN_aan_VegTypeInfo en returned het geheel
        """
        assert len(infos) > 0, "Lijst met VegTypeInfo is leeg"

        new_infos = []
        for info in infos:
            new_infos.append(self.toevoegen_VvN_aan_VegTypeInfo(info))

        return new_infos


def opschonen_was_wordt_lijst(path_in: Path, path_out: Path):
    """
    Ontvangt een was-wordt lijst en output een opgeschoonde was-wordt lijst
    """
    # assert path in is an xlsx file
    assert path_in.suffix == ".xlsx", "Input file is not an xlsx file"
    # assert path out is an xlsx file
    assert path_out.suffix == ".xlsx", "Output file is not an xlsx file"

    wwl = pd.read_excel(path_in, engine="openpyxl", usecols=["VvN", "SBB-code"])
    wwl = wwl.rename(columns={"SBB-code": "SBB"})
    wwl = wwl.dropna(how="all")

    # Rijen met meerdere VvN in 1 cel opsplitsen
    wwl["VvN"] = wwl["VvN"].str.split(",")
    wwl = wwl.explode("VvN")

    # Whitespace velden vervangen door NaN
    wwl = wwl.replace(r"^\s*$", pd.NA, regex=True)

    wwl["VvN"] = opschonen_VvN_pandas_series(wwl["VvN"])
    wwl["SBB"] = opschonen_SBB_pandas_series(wwl["SBB"])

    # Checken
    assert SBB.validate_pandas_series(
        wwl["SBB"], print_invalid=True
    ), "Niet alle SBB codes zijn valid"
    assert VvN.validate_pandas_series(
        wwl["VvN"], print_invalid=True
    ), "Niet alle VvN codes zijn valid"

    wwl.to_excel(path_out, index=False)
