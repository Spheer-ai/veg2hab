import copy
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Union

import pandas as pd

from veg2hab.criteria import BeperkendCriterium
from veg2hab.enums import Kwaliteit
from veg2hab.habitat import HabitatVoorstel
from veg2hab.io.common import Interface
from veg2hab.mozaiek import (  # DummyMozaiekregel,; GeenMozaiekregel,
    MozaiekRegel,
    StandaardMozaiekregel,
)
from veg2hab.vegetatietypen import SBB, VvN
from veg2hab.vegkartering import VegTypeInfo

_LOGGER = logging.getLogger(__name__)


class DefinitieTabel:
    def __init__(self, df: pd.DataFrame):
        # Inladen
        self.df = df

        self.df.Kwaliteit = self.df.Kwaliteit.apply(Kwaliteit.from_letter)
        self.df.SBB = self.df.SBB.apply(SBB.from_string)
        self.df.VvN = self.df.VvN.apply(VvN.from_string)

        assert self.df.mitsjson.notnull().all()

        # Mitsjson parsen
        self.df["Criteria"] = (
            self.df["mitsjson"]
            .loc[self.df["mitsjson"].notnull()]
            .apply(BeperkendCriterium.parse_raw)
        )

        # Mozaiekjson parsen
        self.df["Mozaiekregel"] = (
            self.df["mozaiekjson"]
            .loc[self.df["mozaiekjson"].notnull()]
            .apply(MozaiekRegel.parse_raw)
        )
        # Aanmaken dict keys die gebruikt gaan worden om de mozaiekregels te checken\
        # TODO: Om deze isinstance heenwerken voor modulariteit
        # TODO: Idealiter komt dit een een soort post_init (https://stackoverflow.com/questions/66571079/alter-field-after-instantiation-in-pydantic-basemodel-class)
        self.df["Mozaiekregel"].apply(
            lambda regel: regel.determine_kwalificerende_vegtypen(
                self.df[self.df.Habitattype == regel.kwalificerend_habtype]
            )
            if isinstance(regel, StandaardMozaiekregel) and regel.ook_mozaiekvegetaties
            else None
        )

    @classmethod
    def from_excel(cls, path: Path) -> "DefinitieTabel":
        """
        Maakt een DefinitieTabel object van een excel file.
        Deze method is bedoeld om om te gaan met de opgeschoonde definitietabel uit opschonen_definitietabel().
        """
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
                "mitsjson",
                "mozaiekjson",
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
            # We voegen het percentage en VegTypeInfo los to zodat _find_habtypes_for_code gecached kan worden
            # We moeten een deepcopy maken anders passen we denk ik via referentie de percentages aan in de cache
            voorstel = copy.deepcopy(self._find_habtypes_for_code(code))
            voorstellen += voorstel

        if len(voorstellen) == 0:
            niet_geautomatiseerde_sbb = (
                Interface.get_instance().get_config().niet_geautomatiseerde_sbb
            )
            if len(info.SBB) > 0 and str(info.SBB[0]) in niet_geautomatiseerde_sbb:
                voorstellen.append(HabitatVoorstel.HXXXX_niet_geautomatiseerd_SBB(info))
            else:
                voorstellen.append(HabitatVoorstel.H0000_vegtype_not_in_dt(info))

        return voorstellen

    @lru_cache(maxsize=256)
    def _find_habtypes_for_code(
        self, code: Union[SBB, VvN, None]
    ) -> List[HabitatVoorstel]:
        """
        Maakt een lijst met habitattype voorstellen voor een gegeven code
        Wordt gecached om snelheid te verhogen
        """
        if code is None:
            return []

        voorstellen = []
        column = "VvN" if isinstance(code, VvN) else "SBB"
        match_levels = self.df[column].apply(code.match_up_to)
        max_level = match_levels.max()
        if max_level == 0:
            _LOGGER.debug(f"Geen matchende habitattype gevonden voor {column}: {code}")
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
                    mits=row["Criteria"],
                    mozaiek=row["Mozaiekregel"],
                    match_level=match_levels[idx],
                )
            )

        return voorstellen


def opschonen_definitietabel(
    path_in_deftabel: Path,
    path_in_mitsjson: Path,
    path_in_mozaiekjson: Path,
    path_out: Path,
) -> None:
    """
    Ontvangt een was-wordt lijst en output een opgeschoonde was-wordt lijst.
    Voegt ook json voor de mitsen toe vanuit path_in_json_def.
    """
    assert path_in_deftabel.suffix == ".xls", "Input deftabel file is not an xls file"
    assert (
        path_in_mitsjson.suffix == ".json"
    ), "Input json definitions file is not a json file"
    assert (
        path_in_mozaiekjson.suffix == ".json"
    ), "Input mozaiek json definitions file is not a json file"
    assert path_out.suffix == ".xlsx", "Output file is not an xlsx file"

    ### Inladen
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

    ### Opschonen
    # Verwijderen whitespace in Habitattype
    dt["Habitattype"] = dt["Habitattype"].str.strip()

    # Verwijderen rijen met missende data in VvN
    dt = dt.dropna(subset=["VvN"])

    # Verplaatsen SBB naar eigen kolom
    SBB_mask = dt["VvN"].str.contains("SBB")
    dt.loc[SBB_mask, "SBB"] = dt.loc[SBB_mask, "VvN"]
    dt.loc[SBB_mask, "VvN"] = pd.NA

    dt["SBB"] = SBB.opschonen_series(dt["SBB"])
    dt["VvN"] = VvN.opschonen_series(dt["VvN"])

    # Checken
    assert SBB.validate_pandas_series(
        dt["SBB"], print_invalid=True
    ), "Niet alle SBB codes zijn valid"
    assert VvN.validate_pandas_series(
        dt["VvN"], print_invalid=True
    ), "Niet alle VvN codes zijn valid"

    # Reorder
    dt = dt[["Habitattype", "Kwaliteit", "SBB", "VvN", "mits", "mozaiek"]]

    ### Mits json definities toevoegen
    with open(path_in_mitsjson, "r", encoding="utf-8") as file:
        data = json.load(file)
    mitsjson = pd.DataFrame(
        [{"mits": key, "mitsjson": value} for key, value in data.items()]
    )

    # Checken dat we alle mitsen in dt ook in mitsjson hebben
    for mits in dt.mits.dropna().unique():
        if mits not in mitsjson.mits.unique():
            raise ValueError(f"Mits {mits} is niet gevonden in mitsjson")

    # NaN vervangen door lege strings zodat hier GeenCriteria vanuit mitsjson op matchen
    dt.mits[dt.mits.isna()] = ""
    dt = dt.merge(mitsjson, on="mits", how="left")
    dt["mitsjson"] = dt.mitsjson.apply(json.dumps)

    ### Mozaiek json definities toevoegen
    with open(path_in_mozaiekjson, "r", encoding="utf-8") as file:
        data = json.load(file)
    mozaiekjson = pd.DataFrame(
        [{"mozaiek": key, "mozaiekjson": value} for key, value in data.items()]
    )

    for mozaiek in dt.mozaiek.dropna().unique():
        if mozaiek not in mozaiekjson.mozaiek.unique():
            raise ValueError(f"Mozaiek {mozaiek} is niet gevonden in mozaiekjson")

    # NaN vervangen door lege strings zodat hier GeenMozaiek vanuit mozaiekjson op matchen
    dt["mozaiek"] = dt["mozaiek"].fillna("")
    dt = dt.merge(mozaiekjson, on="mozaiek", how="left")
    dt["mozaiekjson"] = dt.mozaiekjson.apply(json.dumps)

    dt.to_excel(path_out, index=False)
