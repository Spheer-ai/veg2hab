from pathlib import Path

import pandas as pd
import pytest

from veg2hab.vegkartering import VegTypeInfo
from veg2hab.waswordtlijst import WasWordtLijst, opschonen_waswordtlijst


@pytest.fixture(scope="module")
def wwl():
    path_in = (
        Path(__file__).parent
        / ".."
        / "data/5. Was-wordt-lijst-vegetatietypen-en-habitattypen-09-02-2021.xlsx"
    )
    path_out = Path(__file__).resolve().parent / "../testing/opgeschoonde_waswordt.xlsx"
    path_out.parent.mkdir(exist_ok=True)
    opschonen_waswordtlijst(path_in, path_out)
    return WasWordtLijst.from_excel(path_out)


def test_perfect_match_single_sbb_to_vvn(wwl):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["5b2b"])
    post = VegTypeInfo.from_str_vegtypes(
        100, SBB_strings=["5b2b"], VvN_strings=["5ba2"]
    )
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_rvvn_to_single_sbb_vvn(wwl):
    pre = pd.Series([[VegTypeInfo.from_str_vegtypes(100, rVvN_strings=["r1aa1a"])]])
    post = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(
                    100, SBB_strings=["1a1"], VvN_strings=["1aa1a"], rVvN_strings=[]
                )
            ]
        ]
    )
    assert (wwl.van_rVvN_naar_SBB_en_VvN(pre) == post).all()


def test_rvvn_to_multiple_sbb_vvn(wwl):
    pre = pd.Series([[VegTypeInfo.from_str_vegtypes(100, rVvN_strings=["r4ca1"])]])
    post = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(
                    100,
                    SBB_strings=["4d1", "4d1b", "4d1a"],
                    VvN_strings=["4ca1"],
                    rVvN_strings=[],
                )
            ]
        ]
    )
    # Iets uitgebreidere assert hier, omdat door een cast naar een set in wwl.van_rVvN_naar_SBB_en_VvN()
    # om dubbelingen eruit te halen (anders was er in dit geval 3 keer VvN 4ca1) de volgorde van de SBB kan veranderen
    pre = wwl.van_rVvN_naar_SBB_en_VvN(pre)
    assert pre.iloc[0][0].percentage == post.iloc[0][0].percentage
    assert set(pre.iloc[0][0].SBB) == set(post.iloc[0][0].SBB)
    assert set(pre.iloc[0][0].VvN) == set(post.iloc[0][0].VvN)
    assert set(pre.iloc[0][0].rVvN) == set(post.iloc[0][0].rVvN)


def test_nonexistent_single_sbb_to_vvn(wwl):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["7a1z"])
    post = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["7a1z"], VvN_strings=[])
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_empty_sbb(wwl):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=[], VvN_strings=["1aa1"])
    post = VegTypeInfo.from_str_vegtypes(100, SBB_strings=[], VvN_strings=["1aa1"])
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_partial_match_single_sbb_to_vvn(wwl):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["5a2a"])
    post = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["5a2a"], VvN_strings=[])
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_perfect_match_sbb_to_nonexistent_vvn(wwl):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["9b1a"])
    post = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["9b1a"], VvN_strings=[])
    a = wwl.toevoegen_VvN_aan_VegTypeInfo(pre)
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_perfect_match_sbb_to_multiple_vvn(wwl):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["1a1"])
    post = VegTypeInfo.from_str_vegtypes(
        100, SBB_strings=["1a1"], VvN_strings=["1aa1", "1aa1a", "1aa1b"]
    )
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_gemeenschap_single_sbb_to_vvn(wwl):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["5d-b"])
    post = VegTypeInfo.from_str_vegtypes(
        100, SBB_strings=["5d-b"], VvN_strings=["5rg7"]
    )
    assert wwl.toevoegen_VvN_aan_VegTypeInfo(pre) == post


def test_toevoegen_VvN_aan_pandas_series(wwl):
    pre = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(100, SBB_strings=["5b2b"]),
            ],
            [
                VegTypeInfo.from_str_vegtypes(50, SBB_strings=["7a1z"]),
                VegTypeInfo.from_str_vegtypes(50, SBB_strings=["5d-b"]),
            ],
        ]
    )
    post = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(
                    100, SBB_strings=["5b2b"], VvN_strings=["5ba2"]
                ),
            ],
            [
                VegTypeInfo.from_str_vegtypes(50, SBB_strings=["7a1z"], VvN_strings=[]),
                VegTypeInfo.from_str_vegtypes(
                    50, SBB_strings=["5d-b"], VvN_strings=["5rg7"]
                ),
            ],
        ]
    )
    assert (pre.apply(wwl.toevoegen_VvN_aan_List_VegTypeInfo) == post).all()


def test_vervangen_rVvN_in_pandas_series(wwl):
    pre = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(100, SBB_strings=["5b2b"]),
            ],
            [
                VegTypeInfo.from_str_vegtypes(50, SBB_strings=["7a1z"]),
                VegTypeInfo.from_str_vegtypes(50, SBB_strings=["5d-b"]),
            ],
        ]
    )
    post = pd.Series(
        [
            [
                VegTypeInfo.from_str_vegtypes(
                    100, SBB_strings=["5b2b"], VvN_strings=["5ba2"]
                ),
            ],
            [
                VegTypeInfo.from_str_vegtypes(50, SBB_strings=["7a1z"], VvN_strings=[]),
                VegTypeInfo.from_str_vegtypes(
                    50, SBB_strings=["5d-b"], VvN_strings=["5rg7"]
                ),
            ],
        ]
    )
    assert (pre.apply(wwl.toevoegen_VvN_aan_List_VegTypeInfo) == post).all()
