import pytest

from veg2hab.io.cli import CLIInterface
from veg2hab.vegetatietypen import SBB, MatchLevel, VvN
from veg2hab.vegkartering import VegTypeInfo

CLIInterface.get_instance()


def test_vvn_from_str():
    vvn = VvN.from_code("42aa1e")
    assert vvn.klasse == "42"
    assert vvn.orde == "a"
    assert vvn.verbond == "a"
    assert vvn.associatie == "1"
    assert vvn.subassociatie == "e"
    assert vvn.derivaatgemeenschap is None
    assert vvn.rompgemeenschap is None


def test_partial_vvn_from_str():
    vvn = VvN.from_code("42aa")
    assert vvn.klasse == "42"
    assert vvn.orde == "a"
    assert vvn.verbond == "a"
    assert vvn.associatie is None
    assert vvn.subassociatie is None
    assert vvn.derivaatgemeenschap is None
    assert vvn.rompgemeenschap is None


def test_invalid_vvn_from_str():
    with pytest.raises(ValueError):
        vvn = VvN.from_code("some-random-str")


def test_vvn_with_derivaat_gemeenschap():
    vvn = VvN.from_code("42dg2")
    assert vvn.klasse == "42"
    assert vvn.orde is None
    assert vvn.verbond is None
    assert vvn.associatie is None
    assert vvn.subassociatie is None
    assert vvn.derivaatgemeenschap == "2"
    assert vvn.rompgemeenschap is None


def test_vvn_with_rompgemeenschap():
    vvn = VvN.from_code("37rg2")
    assert vvn.klasse == "37"
    assert vvn.orde is None
    assert vvn.verbond is None
    assert vvn.associatie is None
    assert vvn.subassociatie is None
    assert vvn.derivaatgemeenschap is None
    assert vvn.rompgemeenschap == "2"


def test_vvn_rompgemeenschap_is_only_possible_on_klasse():
    with pytest.raises(ValueError):
        vvn = VvN.from_code("37aa17rg2")


def test_match_vvn_codes():
    vvn = VvN.from_code("42aa1e")
    vvn2 = VvN.from_code("42aa")
    vvn3 = VvN.from_code("42aa1f")

    assert (
        vvn.match_up_to(vvn) == MatchLevel.SUBASSOCIATIE_VVN
    ), "Should match all subgroups"
    assert (
        vvn2.match_up_to(vvn2) == MatchLevel.VERBOND_VVN
    ), "Should match all subgroups"

    assert (
        vvn.match_up_to(vvn2) == MatchLevel.VERBOND_VVN
    ), "Should match to less specific VvN"
    assert (
        vvn2.match_up_to(vvn) == MatchLevel.NO_MATCH
    ), "Should not match to more specific VvN"

    assert vvn.match_up_to(vvn3) == MatchLevel.NO_MATCH, "Should not match to unequal"
    assert vvn3.match_up_to(vvn) == MatchLevel.NO_MATCH, "Should not match to unequal"


def test_match_vvn_rompgemeenschap():
    vvn = VvN.from_code("42rg2")
    vvn2 = VvN.from_code("42rg3")
    vvn3 = VvN.from_code("42")

    vvn.match_up_to(vvn2) == MatchLevel.NO_MATCH, "Does not match to other RG"
    vvn.match_up_to(vvn3) == MatchLevel.NO_MATCH, "Does not match to not RG"
    vvn.match_up_to(vvn) == MatchLevel.GEMEENSCHAP_VVN, "Matches to itself"


def test_basic_vvn_equality():
    vvn = VvN.from_code("42aa1e")
    vvn2 = VvN.from_code("42aa1e")
    vvn3 = VvN.from_code("42aa")

    assert vvn == vvn
    assert vvn == vvn2
    assert vvn != vvn3


def test_sbb_from_str():
    sbb = SBB.from_code("42a1e")
    assert sbb.klasse == "42"
    assert sbb.verbond == "a"
    assert sbb.associatie == "1"
    assert sbb.subassociatie == "e"
    assert sbb.derivaatgemeenschap is None
    assert sbb.rompgemeenschap is None


def test_partial_sbb_from_str():
    sbb = SBB.from_code("42a")
    assert sbb.klasse == "42"
    assert sbb.verbond == "a"
    assert sbb.associatie is None
    assert sbb.subassociatie is None
    assert sbb.derivaatgemeenschap is None
    assert sbb.rompgemeenschap is None


def test_invalid_sbb_from_str():
    with pytest.raises(ValueError):
        sbb = SBB.from_code("some-random-str")


def test_sbb_with_derivaat_gemeenschap():
    sbb = SBB.from_code("37/b")
    sbb2 = SBB.from_code("37a3a/b")

    assert sbb.klasse == "37"
    assert sbb.verbond is None
    assert sbb.associatie is None
    assert sbb.subassociatie is None
    assert sbb.derivaatgemeenschap == "b"
    assert sbb.rompgemeenschap is None

    assert sbb2.klasse == "37"
    assert sbb2.verbond == "a"
    assert sbb2.associatie == "3"
    assert sbb2.subassociatie == "a"
    assert sbb2.derivaatgemeenschap == "b"
    assert sbb2.rompgemeenschap is None


def test_sbb_with_rompgemeenschap():
    sbb = SBB.from_code("37-b")
    sbb2 = SBB.from_code("37a3a-b")

    assert sbb.klasse == "37"
    assert sbb.verbond is None
    assert sbb.associatie is None
    assert sbb.subassociatie is None
    assert sbb.derivaatgemeenschap is None
    assert sbb.rompgemeenschap == "b"

    assert sbb2.klasse == "37"
    assert sbb2.verbond == "a"
    assert sbb2.associatie == "3"
    assert sbb2.subassociatie == "a"
    assert sbb2.derivaatgemeenschap is None
    assert sbb2.rompgemeenschap == "b"


def test_match_sbb_codes():
    sbb = SBB.from_code("42a1e")
    sbb2 = SBB.from_code("42a")
    sbb3 = SBB.from_code("42a1f")

    assert (
        sbb.match_up_to(sbb) == MatchLevel.SUBASSOCIATIE_SBB
    ), "Should match all subgroups"
    assert (
        sbb2.match_up_to(sbb2) == MatchLevel.VERBOND_SBB
    ), "Should match all subgroups"

    assert (
        sbb.match_up_to(sbb2) == MatchLevel.VERBOND_SBB
    ), "Should match to less specific sbb"
    assert (
        sbb2.match_up_to(sbb) == MatchLevel.NO_MATCH
    ), "Should not match to more specific sbb"

    assert sbb.match_up_to(sbb3) == MatchLevel.NO_MATCH, "Should not match to unequal"
    assert sbb3.match_up_to(sbb) == MatchLevel.NO_MATCH, "Should not match to unequal"


def test_match_sbb_rompgemeenschap():
    sbb = SBB.from_code("42-b")
    sbb2 = SBB.from_code("42-c")
    sbb3 = SBB.from_code("42")
    sbb4 = SBB.from_code("42a1e-b")

    # NOTE: is dit een logische manier om score te geven? Match to self
    #       geeft 5 zodat de ranking met minder specifieke ssb niet de
    #       voorkeur krijgt.

    sbb.match_up_to(sbb2) == MatchLevel.NO_MATCH, "Does not match to other RG"
    sbb.match_up_to(sbb3) == MatchLevel.NO_MATCH, "Does not match to not RG"
    sbb.match_up_to(sbb) == MatchLevel.GEMEENSCHAP_SBB, "Matches to itself"
    sbb.match_up_to(
        sbb4
    ) == MatchLevel.NO_MATCH, "Does not match to same RG but more specific sbb"
    sbb4.match_up_to(
        sbb
    ) == MatchLevel.NO_MATCH, "Does not match to same RG but less specific sbb"


def test_basic_ssb_equality():
    sbb = SBB.from_code("42a1e")
    sbb2 = SBB.from_code("42a1e")
    sbb3 = SBB.from_code("42a")

    assert sbb == sbb
    assert sbb == sbb2
    assert sbb != sbb3


def test_vegtype_info():
    vegtypeinfo = VegTypeInfo(percentage=100, SBB=[SBB(klasse="42")], VvN=[])

    vegtypeinfo = VegTypeInfo.from_str_vegtypes(
        100, SBB_strings=["42a1e"], VvN_strings=["42aa1e"]
    )
    assert vegtypeinfo.SBB == [SBB.from_code("42a1e")]
