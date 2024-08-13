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
from veg2hab.mozaiek import GeenMozaiekregel, StandaardMozaiekregel
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
            onderbouwend_vegtype=VvN.from_code("25aa3"),
            vegtype_in_dt=VvN.from_code("25aa3"),
            habtype="H1310_A",
            kwaliteit=Kwaliteit.GOED,
            mits=OfCriteria(
                sub_criteria=[
                    FGRCriterium(wanted_fgrtype=FGRType.NZ),
                    FGRCriterium(wanted_fgrtype=FGRType.GG),
                    FGRCriterium(wanted_fgrtype=FGRType.DU),
                    NietGeautomatiseerdCriterium(
                        toelichting='het vlak op andere wijze onder "kustgebied" valt'
                    ),
                ]
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_VVN,
            vegtype_in_dt_naam="Schorrekruid-associatie",
            habtype_naam="Zilte pionierbegroeiingen (zeekraal)",
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_non_existing_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["99aa3a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("99aa3a"),
            vegtype_in_dt=None,
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
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
            onderbouwend_vegtype=VvN.from_code("5ca2a"),
            vegtype_in_dt=VvN.from_code("5ca2"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.GOED,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits in beken of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_VVN,
            vegtype_in_dt_naam="Associatie van Klimopwaterranonkel",
            habtype_naam="Beken en rivieren met waterplanten (waterranonkels)",
        )
    ]
    # Should match with 5ca2
    assert dt.find_habtypes(pre) == post


def test_gemeenschap_perfect_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["5rg8"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("5rg8"),
            vegtype_in_dt=VvN.from_code("5rg8"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.MATIG,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits in beken of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.GEMEENSCHAP_VVN,
            vegtype_in_dt_naam="Rompgemeenschap met Gewoon sterrekroos van de Orde van Haaksterrekroos en Grote waterranonkel",
            habtype_naam="Beken en rivieren met waterplanten (waterranonkels)",
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_match_to_multiple_perfect_matches_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["14bb1a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("14bb1a"),
            vegtype_in_dt=VvN.from_code("14bb1a"),
            habtype="H2330",
            kwaliteit=Kwaliteit.GOED,
            mits=LBKCriterium(wanted_lbktype=LBKType.ZANDVERSTUIVING),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            vegtype_in_dt_naam="Associatie van Schapegras en Tijm (subassociatie met Zandblauwtje)",
            habtype_naam="Zandverstuivingen",
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("14bb1a"),
            vegtype_in_dt=VvN.from_code("14bb1a"),
            habtype="H6120",
            kwaliteit=Kwaliteit.GOED,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits op oeverwallen van rivieren of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            vegtype_in_dt_naam="Associatie van Schapegras en Tijm (subassociatie met Zandblauwtje)",
            habtype_naam="Stroomdalgraslanden",
        ),
    ]

    assert dt.find_habtypes(pre) == post


def test_perfect_and_less_specific_match_VvN(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, VvN_strings=["36aa2a"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("36aa2a"),
            vegtype_in_dt=VvN.from_code("36aa2a"),
            habtype="H2180_B",
            kwaliteit=Kwaliteit.MATIG,
            mits=EnCriteria(
                sub_criteria=[
                    FGRCriterium(wanted_fgrtype=FGRType.DU),
                    NietGeautomatiseerdCriterium(toelichting="zachte berk dominant"),
                ]
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            vegtype_in_dt_naam="Associatie van Grauwe wilg (subassociatie met Hennegras)",
            habtype_naam="Duinbossen (vochtig)",
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("36aa2a"),
            vegtype_in_dt=VvN.from_code("36aa2"),
            habtype="H91D0",
            kwaliteit=Kwaliteit.MATIG,
            mits=GeenCriterium(),
            mozaiek=StandaardMozaiekregel(
                kwalificerend_habtype="H91D0",
                ook_mozaiekvegetaties=False,
                alleen_goede_kwaliteit=False,
                ook_als_rand_langs=True,
            ),
            match_level=MatchLevel.ASSOCIATIE_VVN,
            vegtype_in_dt_naam="Associatie van Grauwe wilg",
            habtype_naam="Hoogveenbossen",
        ),
    ]
    assert dt.find_habtypes(pre) == post


def test_perfect_match_SBB(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["9b1"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("9b1"),
            vegtype_in_dt=SBB.from_code("9b1"),
            habtype="H3160",
            kwaliteit=Kwaliteit.GOED,
            mits=NietGeautomatiseerdCriterium(toelichting="mits in vennen"),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_SBB,
            vegtype_in_dt_naam="Associatie van Slangewortel",
            habtype_naam="Zure vennen",
        )
    ]
    assert dt.find_habtypes(pre) == post


def test_matches_both_vvn_and_sbb(dt):
    pre = VegTypeInfo.from_str_vegtypes(
        100, VvN_strings=["5rg8", "14bb1a"], SBB_strings=["9b1"]
    )
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("5rg8"),
            vegtype_in_dt=VvN.from_code("5rg8"),
            habtype="H3260_A",
            kwaliteit=Kwaliteit.MATIG,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits in beken of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.GEMEENSCHAP_VVN,
            vegtype_in_dt_naam="Rompgemeenschap met Gewoon sterrekroos van de Orde van Haaksterrekroos en Grote waterranonkel",
            habtype_naam="Beken en rivieren met waterplanten (waterranonkels)",
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("14bb1a"),
            vegtype_in_dt=VvN.from_code("14bb1a"),
            habtype="H2330",
            kwaliteit=Kwaliteit.GOED,
            mits=LBKCriterium(wanted_lbktype=LBKType.ZANDVERSTUIVING),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            vegtype_in_dt_naam="Associatie van Schapegras en Tijm (subassociatie met Zandblauwtje)",
            habtype_naam="Zandverstuivingen",
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=VvN.from_code("14bb1a"),
            vegtype_in_dt=VvN.from_code("14bb1a"),
            habtype="H6120",
            kwaliteit=Kwaliteit.GOED,
            mits=NietGeautomatiseerdCriterium(
                toelichting="mits op oeverwallen van rivieren of riviertjes"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_VVN,
            vegtype_in_dt_naam="Associatie van Schapegras en Tijm (subassociatie met Zandblauwtje)",
            habtype_naam="Stroomdalgraslanden",
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("9b1"),
            vegtype_in_dt=SBB.from_code("9b1"),
            habtype="H3160",
            kwaliteit=Kwaliteit.GOED,
            mits=NietGeautomatiseerdCriterium(toelichting="mits in vennen"),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.ASSOCIATIE_SBB,
            vegtype_in_dt_naam="Associatie van Slangewortel",
            habtype_naam="Zure vennen",
        ),
    ]
    post2 = dt.find_habtypes(pre)
    assert dt.find_habtypes(pre) == post

def test_niet_geautomatiseerde_codes(dt):
    pre = VegTypeInfo.from_str_vegtypes(100, SBB_strings=["100"])
    post = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB(klasse="100"),
            vegtype_in_dt=None,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    assert dt.find_habtypes(pre) == post
