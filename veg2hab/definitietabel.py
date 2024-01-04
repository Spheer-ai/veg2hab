from dataclasses import dataclass
from typing import List, Optional, Sequence

import pandas as pd

from veg2hab.criteria import BeperkendCriterium
from veg2hab.enum import GoedMatig


@dataclass
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


class DefinitieTabel:
    data: List[DefinitieRowItem]

    def __init__(self):
        pass

    def from_pandas(self, df):
        self.validate(df)
        pass

    @staticmethod
    def validate(self):
        pass
