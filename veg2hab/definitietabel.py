import copy
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Union

import pandas as pd

from veg2hab.criteria import BeperkendCriterium
from veg2hab.enums import Kwaliteit
from veg2hab.habitat import HabitatVoorstel
from veg2hab.vegetatietypen import (
    SBB,
    VvN,
    convert_string_to_SBB,
    convert_string_to_VvN,
    opschonen_SBB_pandas_series,
    opschonen_VvN_pandas_series,
)
from veg2hab.vegkartering import VegTypeInfo

_LOGGER = logging.getLogger(__name__)


class DefinitieTabel:
    def __init__(self, df: pd.DataFrame):
        # Inladen
        self.df = df

        self.df.Kwaliteit = self.df.Kwaliteit.apply(Kwaliteit.from_letter)
        self.df.SBB = self.df.SBB.apply(convert_string_to_SBB)
        self.df.VvN = self.df.VvN.apply(convert_string_to_VvN)

        self.df["Criteria"] = (
            self.df["json"]
            .loc[self.df["json"].notnull()]
            .apply(BeperkendCriterium.parse_raw)
        )
        self.df.loc[self.df.Criteria.isnull(), "Criteria"] = None
        # TODO parse mozaiek

    @classmethod
    def from_excel(cls, path):
        """
        Maakt een DefinitieTabel object van een excel file.
        Deze method is bedoeld om om te gaan met de opgeschoonde definitietabel uit opschonen_definitietabel().
        """
        # NOTE: Als ik toch de opgeschoonde definitietabel inlaad moet ik dan nog usecols specificeren?
        df = pd.read_excel(
            path,
            engine="openpyxl",
            usecols=[
                "DT regel",
                "Habitattype",
                "Kwaliteit",
                "SBB",
                "VvN",
                "mits",
                "mozaiek",
                "json",
            ],
            dtype="string",
        )
        # NOTE: Ik kan ook wel hierboven een dict meegeven maar dan wordt het lezen van de file zo lang
        df["DT regel"] = df["DT regel"].astype(int)
        return cls(df)

    def find_habtypes(self, info: VegTypeInfo) -> List[HabitatVoorstel]:
        """
        Maakt een lijst met habitattype voorstellen voor een gegeven vegtypeinfo
        """
        voorstellen = []

        for code in info.VvN + info.SBB:
            # We voegen het percentage en VegTypeInfo los to zodat _find_habtypes_for_code gecached kan worden
            # We moeten een deepcopy maken anders passen we denk ik via referentie de percentages aan in de cache
            voorstel = copy.deepcopy(self._find_habtypes_for_code(code))
            for item in voorstel:
                item.percentage = info.percentage
                item.vegtypeinfo = info
            voorstellen += voorstel

        if len(voorstellen) == 0:
            voorstellen.append(HabitatVoorstel.H0000_vegtype_not_in_dt(info))

        return voorstellen

    @lru_cache(maxsize=256)
    def _find_habtypes_for_code(self, code: Union[SBB, VvN]):
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
            vegtype_in_dt = row["SBB"] if isinstance(row["SBB"], SBB) else row["VvN"]
            assert isinstance(vegtype_in_dt, (SBB, VvN))
            voorstellen.append(
                HabitatVoorstel(
                    onderbouwend_vegtype=code,
                    vegtype_in_dt=vegtype_in_dt,
                    habtype=row["Habitattype"],
                    kwaliteit=row["Kwaliteit"],
                    idx_in_dt=row["DT regel"],
                    mits=row["Criteria"],
                    mozaiek=None,  # TODO
                    match_level=match_levels[idx],
                )
            )

        return voorstellen


def opschonen_definitietabel(
    path_in_deftabel: Path, path_in_json_def: Path, path_out: Path
):
    """
    Ontvangt een was-wordt lijst en output een opgeschoonde was-wordt lijst.
    Voegt ook json voor de mitsen toe vanuit path_in_json_def.
    """
    assert path_in_deftabel.suffix == ".xls", "Input deftabel file is not an xls file"
    assert (
        path_in_json_def.suffix == ".csv"
    ), "Input json definitions file is not an csv file"
    assert path_out.suffix == ".xlsx", "Output file is not an xlsx file"

    dt = pd.read_excel(
        path_in_deftabel,
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
    # Toevoegen index als kolom
    dt["DT regel"] = dt.index + 2

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
    dt = dt[["DT regel", "Habitattype", "Kwaliteit", "SBB", "VvN", "mits", "mozaiek"]]

    # TODO: .json van maken
    json_definitions = pd.read_csv(path_in_json_def, sep="|")

    # Checken dat we alle mitsen in dt ook in json_definitions hebben
    for mits in dt.mits.dropna().unique():
        if mits not in json_definitions.mits.unique():
            raise ValueError(f"Mits {mits} is niet gevonden in json_definitions")

    dt = dt.merge(json_definitions, on="mits", how="left")

    dt.to_excel(path_out, index=False)
