from pathlib import Path

import pytest

from veg2hab.definitietabel import DefinitieTabel, opschonen_definitietabel
from veg2hab.enums import GoedMatig
from veg2hab.vegetatietypen import SBB, VvN
from veg2hab.vegkartering import HabitatVoorstel, VegTypeInfo


@pytest.fixture(scope="module")
def dt():
    path_in = Path("data/definitietabel habitattypen (versie 24 maart 2009)_0.xls")
    path_out = Path("testing/opgeschoonde_definitietabel.xlsx")
    path_out.parent.mkdir(exist_ok=True)
    opschonen_definitietabel(path_in, path_out)
    return DefinitieTabel.from_excel(path_out)


def test_perfect_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["25aa3"])
    post = [
        HabitatVoorstel(
            vegtype=VvN("25aa3"),
            habtype="H1310_A",
            kwaliteit=GoedMatig.GOED,
            regel_in_deftabel=12,
            mits=None,
            mozaiek=None,
            match_level=4,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_non_existing_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["99aa3a"])
    assert dt.find_habtypes(pre) == []


def test_match_to_less_specific_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["5ca2a"])
    post = [
        HabitatVoorstel(
            vegtype=VvN("5ca2a"),
            habtype="H3260_A",
            kwaliteit=GoedMatig.GOED,
            regel_in_deftabel=316,
            mits=None,
            mozaiek=None,
            match_level=4,
        )
    ]
    # Should match with 5ca2
    assert dt.find_habtypes(pre) == post


def test_gemeenschap_perfect_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["5rg8"])
    post = [
        HabitatVoorstel(
            vegtype=VvN("5rg8"),
            habtype="H3260_A",
            kwaliteit=GoedMatig.MATIG,
            regel_in_deftabel=319,
            mits=None,
            mozaiek=None,
            match_level=1,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_match_to_multiple_perfect_matches_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["14bb1a"])
    post = [
        HabitatVoorstel(
            vegtype=VvN("14bb1a"),
            habtype="H2330",
            kwaliteit=GoedMatig.GOED,
            regel_in_deftabel=245,
            mits=None,
            mozaiek=None,
            match_level=5,
        ),
        HabitatVoorstel(
            vegtype=VvN("14bb1a"),
            habtype="H6120",
            kwaliteit=GoedMatig.GOED,
            regel_in_deftabel=360,
            mits=None,
            mozaiek=None,
            match_level=5,
        ),
    ]

    assert dt.find_habtypes(pre) == post


def test_perfect_and_less_specific_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["36aa2a"])
    post = [
        HabitatVoorstel(
            vegtype=VvN("36aa2a"),
            habtype="H2180_B",
            kwaliteit=GoedMatig.MATIG,
            regel_in_deftabel=140,
            mits=None,
            mozaiek=None,
            match_level=5,
        ),
        HabitatVoorstel(
            vegtype=VvN("36aa2a"),
            habtype="H91D0",
            kwaliteit=GoedMatig.MATIG,
            regel_in_deftabel=591,
            mits=None,
            mozaiek=None,
            match_level=4,
        ),
    ]
    assert dt.find_habtypes(pre) == post


def test_perfect_match_SBB(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["9b1"])
    post = [
        HabitatVoorstel(
            vegtype=SBB("9b1"),
            habtype="H3160",
            kwaliteit=GoedMatig.GOED,
            regel_in_deftabel=304,
            mits=None,
            mozaiek=None,
            match_level=3,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_matches_both_vvn_and_sbb(dt):
    pre = VegTypeInfo.from_str_vegtypes(
        100, VvN_strings=["5rg8", "14bb1a"], SBB_strings=["9b1"]
    )
    post = [
        HabitatVoorstel(
            vegtype=VvN("5rg8"),
            habtype="H3260_A",
            kwaliteit=GoedMatig.MATIG,
            regel_in_deftabel=319,
            mits=None,
            mozaiek=None,
            match_level=1,
        ),
        HabitatVoorstel(
            vegtype=VvN("14bb1a"),
            habtype="H2330",
            kwaliteit=GoedMatig.GOED,
            regel_in_deftabel=245,
            mits=None,
            mozaiek=None,
            match_level=5,
        ),
        HabitatVoorstel(
            vegtype=VvN("14bb1a"),
            habtype="H6120",
            kwaliteit=GoedMatig.GOED,
            regel_in_deftabel=360,
            mits=None,
            mozaiek=None,
            match_level=5,
        ),
        HabitatVoorstel(
            vegtype=SBB("9b1"),
            habtype="H3160",
            kwaliteit=GoedMatig.GOED,
            regel_in_deftabel=304,
            mits=None,
            mozaiek=None,
            match_level=3,
        ),
    ]
    assert dt.find_habtypes(pre) == post
