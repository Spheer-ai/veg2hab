from pathlib import Path

import pytest

from veg2hab.criteria import (
    EnCriteria,
    FGRCriterium,
    GeenCriterium,
    LBKCriterium,
    NietGeautomatiseerdCriterium,
    OfCriteria,
)
from veg2hab.definitietabel import DefinitieTabel, opschonen_definitietabel
from veg2hab.enums import FGRType, Kwaliteit, LBKType
from veg2hab.habitat import HabitatVoorstel
from veg2hab.io.cli import CLIInterface
from veg2hab.mozaiek import GeenMozaiekregel, NietGeimplementeerdeMozaiekregel
from veg2hab.vegetatietypen import SBB, MatchLevel, VvN
from veg2hab.vegkartering import VegTypeInfo

CLIInterface.get_instance()


@pytest.fixture(scope="module")
def dt():
    path_in = (
        Path(__file__).resolve().parent
        / "../data/definitietabel habitattypen (versie 24 maart 2009)_0.xls"
    )
    path_mitsjson = Path(__file__).resolve().parent / "../data/mitsjson.json"
    path_mozaiekjson = Path(__file__).resolve().parent / "../data/mozaiekjson.json"
    path_out = (
        Path(__file__).resolve().parent / "../testing/opgeschoonde_definitietabel.xlsx"
    )
    path_out.parent.mkdir(exist_ok=True)
    opschonen_definitietabel(path_in, path_mitsjson, path_mozaiekjson, path_out)
    return DefinitieTabel.from_excel(path_out)


def test_perfect_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["25aa3"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("25aa3"),
            vegtype_in_dt=VvN("25aa3"),
            habtype="H1310_A",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=31,
            mits=OfCriteria(
                sub_criteria=[
                    FGRCriterium(fgrtype=FGRType.NZ),
                    FGRCriterium(fgrtype=FGRType.GG),
                    FGRCriterium(fgrtype=FGRType.DU),
                    NietGeautomatiseerdCriterium(
                        toelichting='het vlak op andere wijze onder "kustgebied" valt'
                    ),
                ]
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_VVN,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_non_existing_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["99aa3a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("99aa3a"),
            vegtype_in_dt=None,
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_match_to_less_specific_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["5ca2a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("5ca2a"),
            vegtype_in_dt=VvN("5ca2"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=353,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits in beken of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_VVN,
        )
    ]
    # Should match with 5ca2
    assert dt.find_habtypes(pre) == post


def test_gemeenschap_perfect_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["5rg8"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("5rg8"),
            vegtype_in_dt=VvN("5rg8"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.MATIG,
            idx_in_dt=356,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits in beken of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.GEMEENSCHAP_VVN,
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_match_to_multiple_perfect_matches_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["14bb1a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("14bb1a"),
            vegtype_in_dt=VvN("14bb1a"),
            habtype="H2330",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=276,
            mits=LBKCriterium(lbktype=LBKType.ZANDVERSTUIVING),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("14bb1a"),
            vegtype_in_dt=VvN("14bb1a"),
            habtype="H6120",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=404,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits op oeverwallen van rivieren of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
        ),
    ]

    assert dt.find_habtypes(pre) == post


def test_perfect_and_less_specific_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["36aa2a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("36aa2a"),
            vegtype_in_dt=VvN("36aa2a"),
            habtype="H2180_B",
            kwaliteit=Kwaliteit.MATIG,
            idx_in_dt=169,
            mits=EnCriteria(
                sub_criteria=[
                    FGRCriterium(fgrtype=FGRType.DU),
                    NietGeautomatiseerdCriterium(toelichting="zachte berk dominant"),
                ]
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("36aa2a"),
            vegtype_in_dt=VvN("36aa2"),
            habtype="H91D0",
            kwaliteit=Kwaliteit.MATIG,
            idx_in_dt=640,
            mits=GeenCriterium(),
            mozaiek=NietGeimplementeerdeMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_VVN,
        ),
    ]
    assert dt.find_habtypes(pre) == post


def test_perfect_match_SBB(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["9b1"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("9b1"),
            vegtype_in_dt=SBB("9b1"),
            habtype="H3160",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=340,
            mits=NietGeautomatiseerdCriterium(toelichting="mits in vennen"),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_SBB,
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
            vegtype_in_dt=VvN("5rg8"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.MATIG,
            idx_in_dt=356,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits in beken of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.GEMEENSCHAP_VVN,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("14bb1a"),
            vegtype_in_dt=VvN("14bb1a"),
            habtype="H2330",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=276,
            mits=LBKCriterium(lbktype=LBKType.ZANDVERSTUIVING),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN("14bb1a"),
            vegtype_in_dt=VvN("14bb1a"),
            habtype="H6120",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=404,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits op oeverwallen van rivieren of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("9b1"),
            vegtype_in_dt=SBB("9b1"),
            habtype="H3160",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=340,
            mits=NietGeautomatiseerdCriterium(toelichting="mits in vennen"),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_SBB,
        ),
    ]
    assert dt.find_habtypes(pre) == post


def test_niet_geautomatiseerde_codes(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["100"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("100"),
            vegtype_in_dt=None,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    assert dt.find_habtypes(pre) == post
