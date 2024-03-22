from functools import lru_cache
from pathlib import Path
from typing import List

import pandas as pd

from veg2hab.vegetatietypen import SBB, VvN
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
        self.df["SBB"] = self.df["SBB"].apply(SBB.from_string)
        self.df["VvN"] = self.df["VvN"].apply(VvN.from_string)

        # Replace pd.NA with None
        # NOTE: kunnen we ook alle rows met een NA gewoon verwijderen? Als we of geen VvN of
        #       geen SBB hebben dan kunnen we het toch niet gebruiken voor het omzetten
        self.df = self.df.where(self.df.notnull(), None)

    @classmethod
    def from_excel(cls, path: Path) -> "WasWordtLijst":
        # NOTE: Dus we nemen de "Opmerking vertaling" kolom niet mee? Even checken nog.
        df = pd.read_excel(
            path, engine="openpyxl", usecols=["VvN", "SBB"], dtype="string"
        )
        return cls(df)

    def check_validity_SBB(self, print_invalid: bool = False) -> bool:
        """
        Checkt of de SBB codes in de wwl valide zijn.
        """
        wwl_SBB = self.df["SBB"].astype("string")

        return SBB.validate_pandas_series(wwl_SBB, print_invalid=print_invalid)

    def check_validity_VvN(self, print_invalid: bool = False) -> bool:
        """
        Checkt of de VvN valide in de wwl zijn.
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

    def toevoegen_VvN_aan_VegTypeInfo(self, info: VegTypeInfo) -> VegTypeInfo:
        """
        Zoekt adhv SBB codes de bijbehorende VvN codes in de WWL en voegt deze toe aan de VegTypeInfo
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

    def toevoegen_VvN_aan_List_VegTypeInfo(
        self, infos: List[VegTypeInfo]
    ) -> List[VegTypeInfo]:
        """
        Voert alle elementen in een lijst door toevoegen_VvN_aan_VegTypeInfo en returned het geheel
        Handig voor
        """
        return [self.toevoegen_VvN_aan_VegTypeInfo(info) for info in infos]


def opschonen_was_wordt_lijst(path_in: Path, path_out: Path) -> None:
    """
    Ontvangt een path_in naar de ruwe was-wordt lijst, schoont deze op en slaat het resultaat op in path_out.
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

    # Whitespace velden vervangen door None
    wwl = wwl.replace(r"^\s*$", None, regex=True)

    wwl["VvN"] = VvN.opschonen_series(wwl["VvN"])
    wwl["SBB"] = SBB.opschonen_series(wwl["SBB"])

    # Checken
    assert SBB.validate_pandas_series(
        wwl["SBB"], print_invalid=True
    ), "Niet alle SBB codes zijn valid"
    assert VvN.validate_pandas_series(
        wwl["VvN"], print_invalid=True
    ), "Niet alle VvN codes zijn valid"

    wwl.to_excel(path_out, index=False)
