from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from veg2hab.vegetatietypen import SBB, VvN, rVvN
from veg2hab.vegtypeinfo import VegTypeInfo


class WasWordtLijst:
    def __init__(self, df: pd.DataFrame):
        # Inladen
        self.df = df

        assert df.dtypes["VvN"] == "string", "VvN kolom is geen string"
        assert df.dtypes["SBB"] == "string", "SBB kolom is geen string"
        assert df.dtypes["rVvN"] == "string", "rVvN kolom is geen string"

        # Checken
        self.check_validity_vegtypen()

        # Omvormen naar SBB en VvN klasses
        self.df["SBB"] = self.df["SBB"].apply(SBB.from_string)
        self.df["VvN"] = self.df["VvN"].apply(VvN.from_string)
        self.df["rVvN"] = self.df["rVvN"].apply(rVvN.from_string)

        # Replace pd.NA with None
        self.df = self.df.where(self.df.notnull(), None)

    @classmethod
    def from_excel(cls, path: Path) -> "WasWordtLijst":
        df = pd.read_excel(
            path, engine="openpyxl", usecols=["VvN", "SBB", "rVvN"], dtype="string"
        )
        return cls(df)

    def check_validity_vegtypen(self, print_invalid: bool = False) -> bool:
        """
        Checkt of de VvN valide in de wwl zijn.
        """
        wwl_SBB = self.df["SBB"].astype("string")
        wwl_VvN = self.df["VvN"].astype("string")
        wwl_rVvN = self.df["rVvN"].astype("string")

        assert SBB.validate_pandas_series(
            wwl_SBB, print_invalid=print_invalid
        ), "Niet alle SBB codes zijn valid"
        assert VvN.validate_pandas_series(
            wwl_VvN, print_invalid=print_invalid
        ), "Niet alle VvN codes zijn valid"
        assert rVvN.validate_pandas_series(
            wwl_rVvN, print_invalid=print_invalid
        ), "Niet alle rVvN codes zijn valid"

    @lru_cache(maxsize=256)
    def match_SBB_to_VvN(self, code: SBB) -> List[VvN]:
        """
        Zoekt de VvN codes die bij een SBB code horen
        """
        assert isinstance(code, SBB), "Code is geen SBB object"

        matching_VvN = self.df[self.df.SBB == code].VvN
        # dropna om niet None uit lege VvN cellen in de wwl als VvN te krijgen
        return matching_VvN.dropna().to_list()

    @lru_cache(maxsize=256)
    def match_rVvN_to_VvN_SBB(self, code: rVvN) -> Tuple[List[VvN], List[SBB]]:
        """
        Zoekt de VvN en SBB codes die bij een rVvN code horen
        """
        assert isinstance(code, rVvN), "Code is geen rVvN object"

        matching_VvN = self.df[self.df.rVvN == code].VvN
        matching_SBB = self.df[self.df.rVvN == code].SBB
        # dropna om niet None uit lege VvN cellen in de wwl als VvN/SBB te krijgen
        return matching_VvN.dropna().to_list(), matching_SBB.dropna().to_list()

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
            percentage=info.percentage,
            SBB=info.SBB,
            VvN=new_VvN,
        )

    def toevoegen_VvN_aan_List_VegTypeInfo(
        self, infos: List[VegTypeInfo]
    ) -> List[VegTypeInfo]:
        """
        Voert alle elementen in een lijst door toevoegen_VvN_aan_VegTypeInfo en returned het geheel
        """
        return [self.toevoegen_VvN_aan_VegTypeInfo(info) for info in infos]

    def van_rVvN_naar_SBB_en_VvN(self, vegtypeinfo: pd.Series) -> None:
        """
        Zet een series met lijsten van VegTypeInfos met enkel rVvN om naar een
        series met lijsten van VegTypeInfos met SBB en VvN, zonder rVvN
        """
        assert vegtypeinfo.apply(
            lambda infos: all(
                len(info.VvN) == 0 and len(info.SBB) == 0 for info in infos
            )
        ).all(), "VegTypeInfo in de Series mag geen VvN of SBB bevatten"

        def _rVvN_info_to_SBB_VvN(info: VegTypeInfo) -> VegTypeInfo:
            """
            Zet een VegTypeInfo met alleen rVvN om naar een VegTypeInfo met SBB en VvN
            """
            assert len(info.SBB) == 0, "SBB is niet leeg"
            assert len(info.VvN) == 0, "VvN is niet leeg"
            assert len(info.rVvN) <= 1, "Er zijn meerdere rVvN codes"

            if len(info.rVvN) == 0:
                return VegTypeInfo(
                    percentage=info.percentage,
                    SBB=[],
                    VvN=[],
                    rVvN=[],
                )

            new_VvN, new_SBB = self.match_rVvN_to_VvN_SBB(info.rVvN[0])

            # Cast naar set om dubbelingen te verwijderen
            return VegTypeInfo(
                percentage=info.percentage,
                SBB=list(set(new_SBB)),
                VvN=list(set(new_VvN)),
                rVvN=[],
            )

        return vegtypeinfo.apply(
            lambda infos: [_rVvN_info_to_SBB_VvN(info) for info in infos]
        )


def opschonen_waswordtlijst(path_in: Path, path_out: Path) -> None:
    """
    Ontvangt een path_in naar de ruwe was-wordt lijst, schoont deze op en slaat het resultaat op in path_out.
    """
    # assert path in is an xlsx file
    assert path_in.suffix == ".xlsx", "Input file is not an xlsx file"
    # assert path out is an xlsx file
    assert path_out.suffix == ".xlsx", "Output file is not an xlsx file"

    wwl = pd.read_excel(path_in, engine="openpyxl", usecols=["rVvN", "VvN", "SBB-code"])
    wwl = wwl.rename(columns={"SBB-code": "SBB"})
    wwl = wwl.dropna(how="all")
    wwl = wwl.where(pd.notnull(wwl), None)

    # Rijen met meerdere VvN in 1 cel opsplitsen
    wwl["VvN"] = wwl["VvN"].str.split(",")
    wwl = wwl.explode("VvN")

    # Whitespace velden vervangen door None
    wwl = wwl.replace(r"^\s*$", None, regex=True)

    # Fixen foute rVvN code
    wwl.rVvN.loc[wwl.rVvN == "r43A0A1B"] = "r43AA1B"

    wwl["rVvN"] = rVvN.opschonen_series(wwl["rVvN"])
    wwl["VvN"] = VvN.opschonen_series(wwl["VvN"])
    wwl["SBB"] = SBB.opschonen_series(wwl["SBB"])

    # Checken
    assert SBB.validate_pandas_series(
        wwl["SBB"], print_invalid=True
    ), "Niet alle SBB codes zijn valid"
    assert VvN.validate_pandas_series(
        wwl["VvN"], print_invalid=True
    ), "Niet alle VvN codes zijn valid"
    assert rVvN.validate_pandas_series(
        wwl["rVvN"], print_invalid=True
    ), "Niet alle rVvN codes zijn valid"

    wwl.to_excel(path_out, index=False)
