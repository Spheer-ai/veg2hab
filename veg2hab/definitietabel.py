import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Union

import pandas as pd

from veg2hab.enums import GoedMatig
from veg2hab.vegetatietypen import (
    SBB,
    VvN,
    convert_string_to_SBB,
    convert_string_to_VvN,
    opschonen_SBB_pandas_series,
    opschonen_VvN_pandas_series,
)
from veg2hab.vegkartering import HabitatVoorstel, VegTypeInfo

_LOGGER = logging.getLogger(__name__)


class DefinitieTabel:
    def __init__(self, df: pd.DataFrame):
        # Inladen
        self.df = df

        self.df.Kwaliteit = self.df.Kwaliteit.apply(GoedMatig.from_letter)
        self.df.SBB = self.df.SBB.apply(convert_string_to_SBB)
        self.df.VvN = self.df.VvN.apply(convert_string_to_VvN)

        # TODO parse mits en mozaiek

    @classmethod
    def from_excel(cls, path):
        df = pd.read_excel(
            path,
            engine="openpyxl",
            usecols=[
                "Habitattype",
                "Kwaliteit",
                "SBB",
                "VvN",
                "mits",
                "mozaiek",
            ],
            dtype="string",
        )
        return cls(df)

    def find_habtypes(self, info: VegTypeInfo) -> List[HabitatVoorstel]:
        """
        Maakt een lijst met habitattype voorstellen voor een gegeven vegtypeinfo
        """
        voorstellen = []

        for code in info.VvN + info.SBB:
            voorstel = self._find_habtypes_for_code(code, info.percentage)
            voorstellen += voorstel

        return voorstellen

    @lru_cache(maxsize=256)
    def _find_habtypes_for_code(self, code: Union[SBB, VvN], info_percentage: int):
        """
        Maakt een lijst met habitattype voorstellen voor een gegeven code
        Wordt gecached om snelheid te verhogen
        """
        voorstellen = []
        column = "VvN" if isinstance(code, VvN) else "SBB"
        match_levels = self.df[column].apply(code.match_up_to)
        max_level = match_levels.max()
        if max_level == 0:
            _LOGGER.info(f"Geen matchende habitattype gevonden voor {column}: {code}")
            return []

        match_rows = self.df[match_levels > 0]
        for idx, row in match_rows.iterrows():
            voorstellen.append(
                HabitatVoorstel(
                    vegtype=code,
                    habtype=row["Habitattype"],
                    kwaliteit=row["Kwaliteit"],
                    regel_in_deftabel=idx,
                    mits=None,  # TODO
                    mozaiek=None,  # TODO
                    match_level=match_levels[idx],
                    percentage=info_percentage,
                )
            )

        return voorstellen


def opschonen_definitietabel(path_in: Path, path_out: Path):
    """
    Ontvangt een was-wordt lijst en output een opgeschoonde was-wordt lijst
    """
    assert path_in.suffix == ".xls", "Input file is not an xls file"
    assert path_out.suffix == ".xlsx", "Output file is not an xlsx file"

    dt = pd.read_excel(
        path_in,
        engine="xlrd",
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

    # Reorder
    dt = dt[["Habitattype", "Kwaliteit", "SBB", "VvN", "mits", "mozaiek"]]

    dt.to_excel(path_out, index=False)
