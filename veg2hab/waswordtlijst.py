import math
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
        pass

    @classmethod
    def from_excel(cls, path: Path):
        df = pd.read_excel(path)
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

    def toevoegen_VvN_aan_VegTypeInfo(self, info: VegTypeInfo):
        """
        Zoekt adhv SBB codes de bijbehorende VvN codes en voegt deze toe aan de VegetatieTypeInfo
        """
        if info is None:
            ValueError("VegTypeInfo is None")

        # Als er geen SBB code is
        if info.SBB is None:
            return info

        match_levels = self.df["SBB"].apply(
            lambda x: info.SBB.match_up_to(x) if type(x) == SBB else 0
        )
        max_level = max(match_levels)

        # Als er geen perfecte match is gevonden
        if max_level < info.SBB.max_match_level:
            return VegTypeInfo(info.percentage, SBB=info.SBB, VvN=None)

        possible_VvN = self.df.loc[match_levels == max_level, "VvN"]

        # NOTE: Voor nu even uitgecomment en returnen we gewoon de eerste
        # assert len(possible_VvN) == 1, "Meerdere matchende SBB codes gevonden" + str(possible_VvN[0].SBB) + str(possible_VvN[0].VvN)

        # Als de VvN kolom float is (nan) bij de matchende SBB
        if type(possible_VvN.iloc[0]) == float:
            assert math.isnan(
                possible_VvN.iloc[0]
            ), "VvN kolom is een float maar geen nan"
            return VegTypeInfo(info.percentage, SBB=info.SBB, VvN=None)

        return VegTypeInfo(
            info.percentage,
            SBB=info.SBB,
            VvN=possible_VvN.iloc[0],
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

    wwl = pd.read_excel(path_in, usecols=["VvN", "SBB-code"])
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
