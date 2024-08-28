import json
from numbers import Number
from typing import List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field, validator
from typing_extensions import Self

from veg2hab import vegetatietypen
from veg2hab.enums import WelkeTypologie


class VegTypeInfo(BaseModel):
    """
    Klasse met alle informatie over één vegetatietype van een vlak
    """

    class Config:
        extra = "forbid"
        validate_assignment = True

    percentage: float
    SBB: List[vegetatietypen.SBB] = Field(default_factory=list)
    VvN: List[vegetatietypen.VvN] = Field(default_factory=list)
    rVvN: List[vegetatietypen.rVvN] = Field(default_factory=list)

    # Support voor meerdere rVvN is niet onmogelijk, maar volgensmij niet nodig,
    # en aangezien er in van_rVvN_naar_SBB_en_VvN uit wordt gegaan van maar 1 rVvN,
    # leek me dit valideren wel zo handig
    @validator("rVvN")
    def check_rvvn_length(cls, v):
        if len(v) > 1:
            raise ValueError("Er kan niet meer dan 1 rVvN type zijn")
        return v

    @classmethod
    def from_str_vegtypes(
        cls,
        percentage: Union[None, str, Number],
        VvN_strings: List[Optional[str]] = [],
        SBB_strings: List[Optional[str]] = [],
        rVvN_strings: List[Optional[str]] = [],
    ) -> Self:
        """
        Aanmaken vanuit string vegetatietypen
        """
        if isinstance(percentage, str):
            percentage = float(percentage.replace(",", "."))

        assert isinstance(
            percentage, Number
        ), f"Percentage moet een getal zijn, nu is het {percentage} {type(percentage)}"

        assert (
            len(VvN_strings + SBB_strings + rVvN_strings) > 0
        ), "Er moet minstens 1 vegetatietype zijn"

        vvn = [vegetatietypen.VvN.from_string(i) for i in VvN_strings]
        sbb = [vegetatietypen.SBB.from_string(i) for i in SBB_strings]
        rvvn = [vegetatietypen.rVvN.from_string(i) for i in rVvN_strings]

        return VegTypeInfo(
            percentage=percentage,
            VvN=[v for v in vvn if v is not None],
            SBB=[s for s in sbb if s is not None],
            rVvN=[r for r in rvvn if r is not None],
        )

    @classmethod
    def create_vegtypen_list_from_access_rows(
        cls,
        rows: pd.DataFrame,
        welke_typologie: WelkeTypologie,
        perc_col: str,
        vegtype_col: str,
    ) -> List["VegTypeInfo"]:
        """
        Maakt van alle rijen met vegetatietypes van een vlak
        (via groupby bv) een lijst van VegetatieTypeInfo objecten
        """
        lst = []

        for _, row in rows.iterrows():
            # Als er geen percentage is, willen we ook geen VegTypeInfo,
            if pd.isna(row[perc_col]) or row[perc_col] == 0:
                continue
            # Als er geen vegtypen zijn, willen we ook geen VegTypeInfo,
            if pd.isna(row[vegtype_col]):
                continue
            lst.append(
                cls.from_str_vegtypes(
                    row[perc_col],
                    VvN_strings=[],
                    SBB_strings=[row[vegtype_col]]
                    if vegtype_col and welke_typologie == WelkeTypologie.SBB
                    else [],
                    rVvN_strings=[row[vegtype_col]]
                    if vegtype_col and welke_typologie == WelkeTypologie.rVvN
                    else [],
                )
            )
        return lst

    @staticmethod
    def serialize_list(l: List[Self]) -> str:
        return json.dumps([x.dict() for x in l])

    @staticmethod
    def deserialize_list(s: str) -> List[Self]:
        return [VegTypeInfo(**x) for x in json.loads(s)]

    def __str__(self):
        base = f"({self.percentage}%, SBB: {[str(x) for x in self.SBB]}, VvN: {[str(x) for x in self.VvN]}"
        if len(self.rVvN) > 0:
            return base + f", rVvN: {[str(x) for x in self.rVvN]})"
        return base + ")"

    def __hash__(self):
        return hash((self.percentage, tuple(self.VvN), tuple(self.SBB)))
