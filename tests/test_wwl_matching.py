from pathlib import Path

import pandas as pd
import pytest

from veg2hab.vegkartering import VegTypeInfo
from veg2hab.waswordtlijst import WasWordtLijst, opschonen_was_wordt_lijst

# inladen wwl
path_in = Path("data/5. Was-wordt-lijst-vegetatietypen-en-habitattypen-09-02-2021.xlsx")
path_out = Path("testing/opgeschoonde_waswordt.xlsx")
opschonen_was_wordt_lijst(path_in, path_out)
wwl = WasWordtLijst.from_excel(path_out)


def test_perfect_match_single_sbb_to_vvn():
    pre = VegTypeInfo.from_str_vegtypes(100, SBB="5b2b")
    post = VegTypeInfo.from_str_vegtypes(100, SBB="5b2b", VvN="5ba2")
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_nonexistent_single_sbb_to_vvn():
    pre = VegTypeInfo.from_str_vegtypes(100, SBB="7a1z")
    post = VegTypeInfo.from_str_vegtypes(100, SBB="7a1z", VvN=None)
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_partial_match_single_sbb_to_vvn():
    pre = VegTypeInfo.from_str_vegtypes(100, SBB="5a2a")
    post = VegTypeInfo.from_str_vegtypes(100, SBB="5a2a")
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_perfect_match_sbb_to_nonexistent_vvn():
    pre = VegTypeInfo.from_str_vegtypes(100, SBB="9b1a")
    post = VegTypeInfo.from_str_vegtypes(100, SBB="9b1a", VvN=None)
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_gemeenschap_single_sbb_to_vvn():
    pre = VegTypeInfo.from_str_vegtypes(100, SBB="5d-b")
    post = VegTypeInfo.from_str_vegtypes(100, SBB="5d-b", VvN="5rg7")
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_toevoegen_VvN_aan_pandas_series():
    pre = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(100, SBB="5b2b"),
            ],
            [
                VegTypeInfo.from_str_vegtypes(50, SBB="7a1z"),
                VegTypeInfo.from_str_vegtypes(50, SBB="5d-b"),
            ],
        ]
    )
    post = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(100, SBB="5b2b", VvN="5ba2"),
            ],
            [
                VegTypeInfo.from_str_vegtypes(50, SBB="7a1z", VvN=None),
                VegTypeInfo.from_str_vegtypes(50, SBB="5d-b", VvN="5rg7"),
            ],
        ]
    )
    assert (pre.apply(wwl.toevoegen_VvN_aan_List_VegTypeInfo) == post).all()
