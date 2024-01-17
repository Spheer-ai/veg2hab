
import pytest

from veg2hab.vegetatietypen import SBB, VvN


def test_vvn_from_str():
    vvn = VvN("42aa1e")
    assert vvn.klasse == "42"
    assert vvn.orde == "a"
    assert vvn.verbond == "a"
    assert vvn.associatie == "1"
    assert vvn.subassociatie == "e"
    assert vvn.derivaatgemeenschap is None
    assert vvn.rompgemeenschap is None

def test_partial_vvn_from_str():
    vvn = VvN("42aa")
    assert vvn.klasse == "42"
    assert vvn.orde == "a"
    assert vvn.verbond == "a"
    assert vvn.associatie is None
    assert vvn.subassociatie is None
    assert vvn.derivaatgemeenschap is None
    assert vvn.rompgemeenschap is None

def test_invalid_vvn_from_str():
    with pytest.raises(ValueError):
        vvn = VvN("some-random-str")

def test_vvn_with_derivaat_gemeenschap():
    vvn = VvN("42dg2")
    assert vvn.klasse == "42"
    assert vvn.orde is None
    assert vvn.verbond is None
    assert vvn.associatie is None
    assert vvn.subassociatie is None
    assert vvn.derivaatgemeenschap == "2"
    assert vvn.rompgemeenschap is None

def test_vvn_with_rompgemeenschap():
    vvn = VvN("37rg2")
    assert vvn.klasse == "37"
    assert vvn.orde is None
    assert vvn.verbond is None
    assert vvn.associatie is None
    assert vvn.subassociatie is None
    assert vvn.derivaatgemeenschap is None
    assert vvn.rompgemeenschap == "2"

def test_rompgemeenschap_is_only_possible_on_klasse():
    with pytest.raises(ValueError):
        # NOTE: Wordt dit uitegvoerd? We doen er niks mee
        vvn = VvN("37aa17rg2")


def test_match_vvn_codes():
    vvn = VvN("42aa1e")
    vvn2 = VvN("42aa")
    vvn3 = VvN("42aa1f")

    assert vvn.match_up_to(vvn) == 5, "Should match all subgroups"
    assert vvn2.match_up_to(vvn2) == 3, "Should match all subgroups"

    assert vvn.match_up_to(vvn2) == 3, "Should match to less specific VvN"
    assert vvn2.match_up_to(vvn) == 0, "Should not match to more specific VvN"

    assert vvn.match_up_to(vvn3) == 0, "Should not match to unequal"
    assert vvn3.match_up_to(vvn) == 0, "Should not match to unequal"


def test_match_vvn_rompgemeenschap():
    vvn = VvN("42rg2")
    vvn2 = VvN("42rg3")
    vvn3 = VvN("42")

    vvn.match_up_to(vvn2) == 0, "Does not match to other RG"
    vvn.match_up_to(vvn3) == 0, "Does not match to not RG"
    vvn.match_up_to(vvn) == 1, "Matches to itself"


def test_basic_vvn_equality():
    vvn = VvN("42aa1e")
    vvn2 = VvN("42aa1e")
    vvn3 = VvN("42aa")

    assert vvn == vvn
    assert vvn == vvn2
    assert vvn != vvn3



def test_sbb_from_str():
    sbb = SBB("42a1e")
    assert sbb.klasse == "42"
    assert sbb.verbond == "a"
    assert sbb.associatie == "1"
    assert sbb.subassociatie == "e"
    assert sbb.derivaatgemeenschap is None
    assert sbb.rompgemeenschap is None

def test_partial_sbb_from_str():
    sbb = SBB("42a")
    assert sbb.klasse == "42"
    assert sbb.verbond == "a"
    assert sbb.associatie is None
    assert sbb.subassociatie is None
    assert sbb.derivaatgemeenschap is None
    assert sbb.rompgemeenschap is None

def test_invalid_sbb_from_str():
    with pytest.raises(ValueError):
        sbb = SBB("some-random-str")

def test_sbb_with_derivaat_gemeenschap():
    sbb = SBB("37/b")
    sbb2 = SBB("37a3a/b")

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
    sbb = SBB("37-b")
    sbb2 = SBB("37a3a-b")

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
    sbb = SBB("42a1e")
    sbb2 = SBB("42a")
    sbb3 = SBB("42a1f")

    assert sbb.match_up_to(sbb) == 4, "Should match all subgroups"
    assert sbb2.match_up_to(sbb2) == 2, "Should match all subgroups"

    assert sbb.match_up_to(sbb2) == 3, "Should match to less specific sbb"
    assert sbb2.match_up_to(sbb) == 0, "Should not match to more specific sbb"

    assert sbb.match_up_to(sbb3) == 0, "Should not match to unequal"
    assert sbb3.match_up_to(sbb) == 0, "Should not match to unequal"


def test_match_sbb_rompgemeenschap():
    sbb = SBB("42-b")
    sbb2 = SBB("42-c")
    sbb3 = SBB("42")
    sbb4 = SBB("42a1e-b")

    # NOTE: is dit een logische manier om score te geven? Match to self 
    #       geeft 5 zodat de ranking met minder specifieke ssb niet de
    #       voorkeur krijgt.

    sbb.match_up_to(sbb2) == 0, "Does not match to other RG"
    sbb.match_up_to(sbb3) == 0, "Does not match to not RG"
    sbb.match_up_to(sbb) == 5, "Matches to itself"
    sbb.match_up_to(sbb4) == 0, "Does not match to same RG but more specific sbb"
    sbb4.match_up_to(sbb) == 1, "Does match to same RG but less specific sbb"


def test_basic_ssb_equality():
    sbb = SBB("42a1e")
    sbb2 = SBB("42a1e")
    sbb3 = SBB("42a")

    assert sbb == sbb
    assert sbb == sbb2
    assert sbb != sbb3





# NOTE: deze kan weg toch
# def test_vvn_validate():
#     # Valid code
#     assert VvN.validate("42aa1e") == True

#     # Invalid code with extra characters
#     assert VvN.validate("42a1e") == False

#     # Invalid code with leading zero
#     assert VvN.validate("08bb02") == False

#     # Invalid code with missing characters
#     assert VvN.validate("42a") == False

# def test_vvn_validate_pandas_series():
#     # Create a pandas series with codes
#     series = pd.Series(["42aa1e", "42a1e", "08bb02", "42a"])

#     # Validate the series
#     invalid_mask = VvN.validate_pandas_series(series)

#     # Check if the invalid mask is correct
#     assert invalid_mask.tolist() == [False, True, True, True]
