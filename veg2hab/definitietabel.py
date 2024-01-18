from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd

from veg2hab.criteria import BeperkendCriterium
from veg2hab.enums import GoedMatig
from veg2hab.vegetatietypen import (
    SBB,
    VvN,
    opschonen_SBB_pandas_series,
    opschonen_VvN_pandas_series,
)

# From early pair programming session
# Commented out in order to work on the rest
"""@dataclass
class DefinitieRowItem:
    row_idx: int
    VvN: Optional[str]  # enum?
    SBB: Optional[str]  # enum?
    HABCODE: str  # enum?
    Kwaliteit: GoedMatig
    mits: BeperkendCriterium
    mozaiek: MozaiekRegel

    def __post_init__(self):
        if (self.VvN is None) != (self.SBB is None):
            raise ValueError("Precies een van VvN of SBB moet een waarde hebben")
"""


class DefinitieTabel:
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

    def check_validity_VvN(self, print_invalid: bool = False):
        """
        Checkt of de VvN valide zijn.
        """
        dt_VvN = self.df["VvN"].astype("string")

        return VvN.validate_pandas_series(dt_VvN, print_invalid=print_invalid)

    def check_validity_SBB(self, print_invalid: bool = False):
        """
        Checkt of de SBB valide zijn.
        """
        dt_SBB = self.df["SBB"].astype("string")

        return SBB.validate_pandas_series(dt_SBB, print_invalid=print_invalid)


def opschonen_definitietabel(path_in: Path, path_out: Path):
    """
    Ontvangt een was-wordt lijst en output een opgeschoonde was-wordt lijst
    """
    # assert path in is an xlsx file
    assert path_in.suffix == ".xls", "Input file is not an xls file"
    # assert path out is an xlsx file
    assert path_out.suffix == ".xlsx", "Output file is not an xlsx file"

    dt = pd.read_excel(
        path_in,
        usecols=[
            "Code habitat (sub)type",
            "Goed / Matig",
            "Code vegetatietype",
            "beperkende criteria",
            "alleen in mozaïek",
        ],
    )
    # Hernoemen kolommen
    dt = dt.rename(
        columns={
            "Code habitat (sub)type": "Habitattype",
            "Goed / Matig": "Kwaliteit",
            "Code vegetatietype": "VvN",
            "beperkende criteria": "mits",
            "alleen in mozaïek": "mozaiek",
        }
    )

    # Verwijderen rijen met missende data in VvN
    dt = dt.dropna(subset=["VvN"])

    # Verplaatsen SBB naar eigen kolom
    SBB_mask = dt["VvN"].str.contains("SBB")
    dt.loc[SBB_mask, "SBB"] = dt.loc[SBB_mask, "VvN"]
    dt.loc[SBB_mask, "VvN"] = pd.NA

    dt["SBB"] = opschonen_SBB_pandas_series(dt["SBB"])
    dt["VvN"] = opschonen_VvN_pandas_series(dt["VvN"])

    # Checken
    assert SBB.validate_pandas_series(
        dt["SBB"], print_invalid=True
    ), "Niet alle SBB codes zijn valid"
    assert VvN.validate_pandas_series(
        dt["VvN"], print_invalid=True
    ), "Niet alle VvN codes zijn valid"

    dt.to_excel(path_out, index=False)
