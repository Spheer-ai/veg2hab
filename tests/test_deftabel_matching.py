from pathlib import Path

import pytest

from veg2hab.criteria import (
    EnCriteria,
    FGRCriterium,
    NietCriterium,
    OfCriteria,
    PlaceholderCriterium,
)
from veg2hab.definitietabel import DefinitieTabel, opschonen_definitietabel
from veg2hab.enums import Kwaliteit
from veg2hab.fgr import FGRType
from veg2hab.habitat import HabitatVoorstel
from veg2hab.vegetatietypen import SBB, MatchLevel, VvN
from veg2hab.vegkartering import VegTypeInfo


@pytest.fixture(scope="module")
def dt():
    path_in = Path("data/definitietabel habitattypen (versie 24 maart 2009)_0.xls")
    path_json = Path("data/definitietabel_json.csv")
    path_out = Path("testing/opgeschoonde_definitietabel.xlsx")
    path_out.parent.mkdir(exist_ok=True)
    opschonen_definitietabel(path_in, path_json, path_out)
    return DefinitieTabel.from_excel(path_out)


def test_perfect_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["25aa3"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("25aa3"),
            habtype="H1310_A",
            kwaliteit=Kwaliteit.GOED,
            idx_opgeschoonde_dt=12,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.ASSOCIATIE_VVN,
            percentage=100,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_non_existing_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["99aa3a"])
    # NOTE: Hier al H0000?
    assert dt.find_habtypes(pre) == []


def test_match_to_less_specific_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["5ca2a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("5ca2a"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.GOED,
            idx_opgeschoonde_dt=316,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.ASSOCIATIE_VVN,
            percentage=100,
        )
    ]
    # Should match with 5ca2
    assert dt.find_habtypes(pre) == post


def test_gemeenschap_perfect_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["5rg8"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("5rg8"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.MATIG,
            idx_opgeschoonde_dt=319,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.GEMEENSCHAP_VVN,
            percentage=100,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_match_to_multiple_perfect_matches_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["14bb1a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("14bb1a"),
            habtype="H2330",
            kwaliteit=Kwaliteit.GOED,
            idx_opgeschoonde_dt=245,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            percentage=100,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("14bb1a"),
            habtype="H6120",
            kwaliteit=Kwaliteit.GOED,
            idx_opgeschoonde_dt=360,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            percentage=100,
        ),
    ]

    assert dt.find_habtypes(pre) == post


def test_perfect_and_less_specific_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["36aa2a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("36aa2a"),
            habtype="H2180_B",
            kwaliteit=Kwaliteit.MATIG,
            idx_opgeschoonde_dt=140,
            mits=EnCriteria(
                sub_criteria=[FGRCriterium(fgrtype=FGRType.DU), PlaceholderCriterium()]
            ),
            mozaiek=None,
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            percentage=100,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("36aa2a"),
            habtype="H91D0",
            kwaliteit=Kwaliteit.MATIG,
            idx_opgeschoonde_dt=591,
            mits=None,
            mozaiek=None,
            match_level=MatchLevel.ASSOCIATIE_VVN,
            percentage=100,
        ),
    ]
    assert dt.find_habtypes(pre) == post


def test_perfect_match_SBB(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["9b1"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("9b1"),
            habtype="H3160",
            kwaliteit=Kwaliteit.GOED,
            idx_opgeschoonde_dt=304,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.ASSOCIATIE_SBB,
            percentage=100,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_matches_both_vvn_and_sbb(dt):
    pre = VegTypeInfo.from_str_vegtypes(
        100, VvN_strings=["5rg8", "14bb1a"], SBB_strings=["9b1"]
    )
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("5rg8"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.MATIG,
            idx_opgeschoonde_dt=319,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.GEMEENSCHAP_VVN,
            percentage=100,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("14bb1a"),
            habtype="H2330",
            kwaliteit=Kwaliteit.GOED,
            idx_opgeschoonde_dt=245,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            percentage=100,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("14bb1a"),
            habtype="H6120",
            kwaliteit=Kwaliteit.GOED,
            idx_opgeschoonde_dt=360,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            percentage=100,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("9b1"),
            habtype="H3160",
            kwaliteit=Kwaliteit.GOED,
            idx_opgeschoonde_dt=304,
            mits=PlaceholderCriterium(),
            mozaiek=None,
            match_level=MatchLevel.ASSOCIATIE_SBB,
            percentage=100,
        ),
    ]
    assert dt.find_habtypes(pre) == post
