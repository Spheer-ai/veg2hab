from pathlib import Path

import pandas as pd

from veg2hab.vegetatietypen import (
    SBB,
    VvN,
    opschonen_SBB_pandas_series,
    opschonen_VvN_pandas_series,
)


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

    @classmethod
    def from_excel(cls, path):
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
